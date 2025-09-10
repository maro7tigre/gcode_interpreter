"""
Main G-code processor interface.
This is the primary entry point for the G-code interpreter.
"""
from typing import List, Dict, Any, Optional, Tuple
from core.interpreter import GCodeInterpreter
from core.geometry import GeometrySegment, MoveType
from utils.errors import GCodeError


class GCodeProcessor:
    """
    Main interface for G-code processing.
    Provides a simple API for text editors and 3D visualization tools.
    """
    
    def __init__(self):
        self.interpreter = GCodeInterpreter()
        self._last_processed_text = ""
        self._processing_successful = False
    
    def process_gcode(self, gcode_text: str) -> bool:
        """
        Process G-code text and generate toolpath geometry.
        
        Args:
            gcode_text: Raw G-code text to process
            
        Returns:
            True if processing succeeded without fatal errors
        """
        self._last_processed_text = gcode_text
        self._processing_successful = self.interpreter.process_gcode(gcode_text)
        return self._processing_successful
    
    def validate_syntax(self, gcode_text: str) -> bool:
        """
        Validate G-code syntax without full execution.
        Useful for real-time editor feedback.
        
        Args:
            gcode_text: Raw G-code text to validate
            
        Returns:
            True if syntax is valid
        """
        return self.interpreter.validate_syntax_only(gcode_text)
    
    # Error handling methods for editor integration
    
    def get_errors_for_line(self, line_number: int) -> List[GCodeError]:
        """Get all errors for a specific line number."""
        return self.interpreter.get_errors_for_line(line_number)
    
    def get_all_errors(self) -> List[GCodeError]:
        """Get all errors from the last processing."""
        return self.interpreter.get_all_errors()
    
    def has_errors(self) -> bool:
        """Check if there are any errors (excluding warnings)."""
        return self.interpreter.error_collector.has_errors()
    
    def has_fatal_errors(self) -> bool:
        """Check if there are any fatal errors."""
        return self.interpreter.error_collector.has_fatal_errors()
    
    # Geometry methods for 3D visualization
    
    def get_geometry_for_line(self, line_number: int) -> List[GeometrySegment]:
        """Get all geometry segments for a specific line number."""
        return self.interpreter.get_geometry_for_line(line_number)
    
    def get_all_geometry(self) -> List[GeometrySegment]:
        """Get all geometry segments."""
        return self.interpreter.get_all_geometry()
    
    def get_rapid_moves(self) -> List[GeometrySegment]:
        """Get all rapid movement geometry."""
        return self.interpreter.get_geometry_by_type(MoveType.RAPID)
    
    def get_feed_moves(self) -> List[GeometrySegment]:
        """Get all feed movement geometry."""
        return self.interpreter.get_geometry_by_type(MoveType.FEED)
    
    def get_arc_moves(self) -> List[GeometrySegment]:
        """Get all arc movement geometry."""
        arcs = self.interpreter.get_geometry_by_type(MoveType.ARC_CW)
        arcs.extend(self.interpreter.get_geometry_by_type(MoveType.ARC_CCW))
        return arcs
    
    def get_bounding_box(self) -> Tuple[List[float], List[float]]:
        """
        Get the bounding box of all geometry.
        
        Returns:
            Tuple of (min_point, max_point) as [x, y, z] lists
        """
        min_point, max_point = self.interpreter.get_bounding_box()
        return min_point.to_list(), max_point.to_list()
    
    # Statistics and information methods
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing and toolpath statistics."""
        return self.interpreter.get_statistics()
    
    def get_machine_state(self) -> Dict[str, Any]:
        """Get current machine state summary."""
        return self.interpreter.machine_state.get_state_summary()
    
    def was_processing_successful(self) -> bool:
        """Check if the last processing was successful."""
        return self._processing_successful
    
    def get_last_processed_text(self) -> str:
        """Get the text that was last processed."""
        return self._last_processed_text
    
    # Utility methods
    
    def reset(self):
        """Reset processor to initial state."""
        self.interpreter.reset()
        self._last_processed_text = ""
        self._processing_successful = False
    
    def highlight_geometry_for_line(self, line_number: int) -> List[int]:
        """
        Get segment IDs that should be highlighted for a given line.
        Useful for editor-to-3D view synchronization.
        
        Args:
            line_number: The line number to highlight
            
        Returns:
            List of segment IDs to highlight
        """
        segments = self.get_geometry_for_line(line_number)
        return [seg.segment_id for seg in segments]
    
    def get_line_for_geometry(self, segment_id: int) -> Optional[int]:
        """
        Get the line number that generated a specific geometry segment.
        Useful for 3D view-to-editor synchronization.
        
        Args:
            segment_id: The geometry segment ID
            
        Returns:
            Line number or None if segment not found
        """
        all_segments = self.get_all_geometry()
        for segment in all_segments:
            if segment.segment_id == segment_id:
                return segment.line_number
        return None
    
    def get_toolpath_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the toolpath for display purposes.
        
        Returns:
            Dictionary with toolpath summary information
        """
        stats = self.get_statistics()
        min_point, max_point = self.get_bounding_box()
        
        return {
            'total_length': stats['geometry']['total_length'],
            'rapid_length': stats['geometry']['rapid_length'],
            'feed_length': stats['geometry']['feed_length'],
            'total_segments': stats['geometry']['total_segments'],
            'bounding_box': {
                'min': min_point,
                'max': max_point,
                'size': [
                    max_point[0] - min_point[0],
                    max_point[1] - min_point[1],
                    max_point[2] - min_point[2]
                ]
            },
            'move_types': {
                'rapid': stats['geometry']['rapid_segments'],
                'feed': stats['geometry']['feed_segments'],
                'arc': stats['geometry']['arc_segments']
            }
        }


# Example usage and testing
if __name__ == "__main__":
    # Simple test of the processor
    processor = GCodeProcessor()
    
    # Test G-code
    test_gcode = """
G21 G90 G94  ; Metric, absolute, feed rate mode
G0 X0 Y0 Z5  ; Rapid to start position
G1 Z0 F1000  ; Plunge to work surface
G1 X10 Y0    ; Linear move
G2 X20 Y10 I10 J0  ; Clockwise arc
G1 X30 Y10   ; Another linear move
G0 Z5        ; Rapid retract
M30          ; Program end
"""
    
    print("Processing test G-code...")
    success = processor.process_gcode(test_gcode)
    
    print(f"Processing successful: {success}")
    print(f"Errors: {len(processor.get_all_errors())}")
    print(f"Geometry segments: {len(processor.get_all_geometry())}")
    
    if processor.get_all_errors():
        print("\nErrors found:")
        for error in processor.get_all_errors():
            print(f"  Line {error.line_number}: {error.message}")
    
    stats = processor.get_toolpath_summary()
    print(f"\nToolpath summary:")
    print(f"  Total length: {stats['total_length']:.2f}")
    print(f"  Feed length: {stats['feed_length']:.2f}")
    print(f"  Rapid length: {stats['rapid_length']:.2f}")
    print(f"  Bounding box: {stats['bounding_box']['size']}")