"""
Geometry management for G-code interpreter.
Handles creation and tracking of toolpath geometry with line mapping.
"""
import math
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum


class MoveType(Enum):
    RAPID = "rapid"
    FEED = "feed"
    ARC_CW = "arc_cw"
    ARC_CCW = "arc_ccw"


@dataclass
class Point3D:
    """Represents a 3D point."""
    x: float
    y: float
    z: float
    
    def to_list(self) -> List[float]:
        """Convert to list format."""
        return [self.x, self.y, self.z]
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)


@dataclass
class GeometrySegment:
    """Represents a single geometry segment in the toolpath."""
    segment_id: int
    line_number: int
    move_type: MoveType
    start_point: Point3D
    end_point: Point3D
    
    # Arc-specific properties
    center_point: Optional[Point3D] = None
    radius: Optional[float] = None
    start_angle: Optional[float] = None
    end_angle: Optional[float] = None
    plane: Optional[str] = None  # 'XY', 'XZ', 'YZ'
    
    # Additional properties
    feed_rate: Optional[float] = None
    length: Optional[float] = None
    
    def calculate_length(self) -> float:
        """Calculate the length of this segment."""
        if self.move_type in [MoveType.RAPID, MoveType.FEED]:
            # Linear move
            self.length = self.start_point.distance_to(self.end_point)
        elif self.move_type in [MoveType.ARC_CW, MoveType.ARC_CCW]:
            # Arc move
            if self.radius is not None and self.start_angle is not None and self.end_angle is not None:
                angle_diff = abs(self.end_angle - self.start_angle)
                # Handle angle wraparound
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                self.length = self.radius * angle_diff
            else:
                # Fallback to straight line distance
                self.length = self.start_point.distance_to(self.end_point)
        
        return self.length or 0.0
    
    def get_bounding_box(self) -> Tuple[Point3D, Point3D]:
        """Get the bounding box of this segment."""
        if self.move_type in [MoveType.RAPID, MoveType.FEED]:
            # Linear move - simple min/max
            min_point = Point3D(
                min(self.start_point.x, self.end_point.x),
                min(self.start_point.y, self.end_point.y),
                min(self.start_point.z, self.end_point.z)
            )
            max_point = Point3D(
                max(self.start_point.x, self.end_point.x),
                max(self.start_point.y, self.end_point.y),
                max(self.start_point.z, self.end_point.z)
            )
            return min_point, max_point
        else:
            # Arc move - more complex calculation needed
            # For now, use simple approach with start/end points
            # TODO: Calculate actual arc bounding box
            return self.get_bounding_box()


class GeometryManager:
    """Manages toolpath geometry and maintains line-to-geometry mapping."""
    
    def __init__(self):
        self.segments: List[GeometrySegment] = []
        self.line_to_segments: Dict[int, List[int]] = {}  # line_number -> segment_ids
        self.segment_counter = 0
        
        # Statistics
        self.total_length = 0.0
        self.rapid_length = 0.0
        self.feed_length = 0.0
        
    def add_linear_move(self, start: List[float], end: List[float], 
                       line_number: int, move_type: MoveType, 
                       feed_rate: Optional[float] = None) -> int:
        """Add a linear move to the geometry."""
        start_point = Point3D(start[0], start[1], start[2])
        end_point = Point3D(end[0], end[1], end[2])
        
        segment = GeometrySegment(
            segment_id=self.segment_counter,
            line_number=line_number,
            move_type=move_type,
            start_point=start_point,
            end_point=end_point,
            feed_rate=feed_rate
        )
        
        # Calculate length
        length = segment.calculate_length()
        self.total_length += length
        
        if move_type == MoveType.RAPID:
            self.rapid_length += length
        elif move_type == MoveType.FEED:
            self.feed_length += length
        
        # Add to collections
        self.segments.append(segment)
        self._add_line_mapping(line_number, self.segment_counter)
        
        self.segment_counter += 1
        return segment.segment_id
    
    def add_arc_move(self, start: List[float], end: List[float], 
                    center: List[float], line_number: int, 
                    direction: str, plane: str = 'XY',
                    feed_rate: Optional[float] = None) -> int:
        """Add an arc move to the geometry."""
        start_point = Point3D(start[0], start[1], start[2])
        end_point = Point3D(end[0], end[1], end[2])
        center_point = Point3D(center[0], center[1], center[2])
        
        move_type = MoveType.ARC_CW if direction.upper() == 'CW' else MoveType.ARC_CCW
        
        # Calculate arc properties
        radius, start_angle, end_angle = self._calculate_arc_properties(
            start_point, end_point, center_point, plane, direction
        )
        
        segment = GeometrySegment(
            segment_id=self.segment_counter,
            line_number=line_number,
            move_type=move_type,
            start_point=start_point,
            end_point=end_point,
            center_point=center_point,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            plane=plane,
            feed_rate=feed_rate
        )
        
        # Calculate length
        length = segment.calculate_length()
        self.total_length += length
        self.feed_length += length  # Arcs are always feed moves
        
        # Add to collections
        self.segments.append(segment)
        self._add_line_mapping(line_number, self.segment_counter)
        
        self.segment_counter += 1
        return segment.segment_id
    
    def get_segments_for_line(self, line_number: int) -> List[GeometrySegment]:
        """Get all geometry segments for a specific line number."""
        segment_ids = self.line_to_segments.get(line_number, [])
        return [self.segments[sid] for sid in segment_ids if sid < len(self.segments)]
    
    def get_all_segments(self) -> List[GeometrySegment]:
        """Get all geometry segments."""
        return self.segments.copy()
    
    def get_segments_by_type(self, move_type: MoveType) -> List[GeometrySegment]:
        """Get all segments of a specific type."""
        return [seg for seg in self.segments if seg.move_type == move_type]
    
    def get_bounding_box(self) -> Tuple[Point3D, Point3D]:
        """Get the overall bounding box of all geometry."""
        if not self.segments:
            return Point3D(0, 0, 0), Point3D(0, 0, 0)
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for segment in self.segments:
            # Check start and end points
            for point in [segment.start_point, segment.end_point]:
                min_x = min(min_x, point.x)
                min_y = min(min_y, point.y)
                min_z = min(min_z, point.z)
                max_x = max(max_x, point.x)
                max_y = max(max_y, point.y)
                max_z = max(max_z, point.z)
        
        return Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get toolpath statistics."""
        return {
            'total_segments': len(self.segments),
            'rapid_segments': len(self.get_segments_by_type(MoveType.RAPID)),
            'feed_segments': len(self.get_segments_by_type(MoveType.FEED)),
            'arc_segments': len(self.get_segments_by_type(MoveType.ARC_CW)) + 
                           len(self.get_segments_by_type(MoveType.ARC_CCW)),
            'total_length': self.total_length,
            'rapid_length': self.rapid_length,
            'feed_length': self.feed_length,
            'lines_with_geometry': len(self.line_to_segments)
        }
    
    def clear(self):
        """Clear all geometry data."""
        self.segments.clear()
        self.line_to_segments.clear()
        self.segment_counter = 0
        self.total_length = 0.0
        self.rapid_length = 0.0
        self.feed_length = 0.0
    
    def _add_line_mapping(self, line_number: int, segment_id: int):
        """Add mapping from line number to segment ID."""
        if line_number not in self.line_to_segments:
            self.line_to_segments[line_number] = []
        self.line_to_segments[line_number].append(segment_id)
    
    def _calculate_arc_properties(self, start: Point3D, end: Point3D, 
                                 center: Point3D, plane: str, 
                                 direction: str) -> Tuple[float, float, float]:
        """Calculate arc radius and angles."""
        # Determine which axes to use based on plane
        if plane.upper() == 'XY':
            x1, y1 = start.x, start.y
            x2, y2 = end.x, end.y
            cx, cy = center.x, center.y
        elif plane.upper() == 'XZ':
            x1, y1 = start.x, start.z
            x2, y2 = end.x, end.z
            cx, cy = center.x, center.z
        elif plane.upper() == 'YZ':
            x1, y1 = start.y, start.z
            x2, y2 = end.y, end.z
            cx, cy = center.y, center.z
        else:
            # Default to XY
            x1, y1 = start.x, start.y
            x2, y2 = end.x, end.y
            cx, cy = center.x, center.y
        
        # Calculate radius (average of start and end radii for better accuracy)
        r1 = math.sqrt((x1 - cx)**2 + (y1 - cy)**2)
        r2 = math.sqrt((x2 - cx)**2 + (y2 - cy)**2)
        radius = (r1 + r2) / 2
        
        # Calculate angles
        start_angle = math.atan2(y1 - cy, x1 - cx)
        end_angle = math.atan2(y2 - cy, x2 - cx)
        
        # Normalize angles to [0, 2π]
        if start_angle < 0:
            start_angle += 2 * math.pi
        if end_angle < 0:
            end_angle += 2 * math.pi
        
        return radius, start_angle, end_angle