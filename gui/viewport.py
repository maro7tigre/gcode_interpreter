"""
Enhanced OpenGL viewport for rendering G-code toolpath with the new geometry system.
"""
import math
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *
from core.geometry import MoveType, GeometrySegment


class Viewport(QOpenGLWidget):
    """3D viewport for displaying G-code toolpath using the new geometry system."""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Geometry data from new system
        self.geometry_segments = []
        self.highlighted_lines = set()
        
        # Camera controls
        self.zoom = -30.0
        self.x_rot = -30.0
        self.y_rot = 0.0
        self.z_rot = 30.0
        self.last_pos = QPoint()
        
        # Display settings
        self.show_rapid = True
        self.show_feed = True
        self.show_arcs = True
        self.show_grid = True
        self.show_axes = True

    def set_geometry(self, segments):
        """Update with new geometry segments from processor."""
        self.geometry_segments = segments or []
        self.auto_fit_view()
        self.update()

    def highlight_lines(self, line_numbers):
        """Highlight segments from specific G-code lines."""
        self.highlighted_lines = set(line_numbers) if line_numbers else set()
        self.update()

    def auto_fit_view(self):
        """Automatically fit camera to show all geometry."""
        if not self.geometry_segments:
            return
        
        # Calculate bounds
        points = []
        for seg in self.geometry_segments:
            points.extend([seg.start_point, seg.end_point])
        
        if not points:
            return
        
        xs = [p.x for p in points]
        ys = [p.y for p in points] 
        zs = [p.z for p in points]
        
        size = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        self.zoom = -max(size * 1.5, 10.0)

    def initializeGL(self):
        """Setup OpenGL context."""
        glClearColor(0.1, 0.1, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        """Handle window resize."""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h if h > 0 else 1, 0.1, 1000.0)

    def paintGL(self):
        """Main render loop."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Apply camera transform
        glTranslatef(0, 0, self.zoom)
        glRotatef(self.x_rot, 1, 0, 0)
        glRotatef(self.y_rot, 0, 1, 0)
        glRotatef(self.z_rot, 0, 0, 1)

        # Draw scene
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        
        self.draw_toolpath()

    def draw_grid(self):
        """Draw reference grid."""
        glLineWidth(1.0)
        glColor3f(0.3, 0.3, 0.3)
        
        glBegin(GL_LINES)
        for i in range(-50, 51, 5):
            glVertex3f(i, -50, 0)
            glVertex3f(i, 50, 0)
            glVertex3f(-50, i, 0)
            glVertex3f(50, i, 0)
        glEnd()

    def draw_axes(self):
        """Draw coordinate axes."""
        glLineWidth(3.0)
        
        glBegin(GL_LINES)
        # X axis - Red
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(15, 0, 0)
        
        # Y axis - Green  
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 15, 0)
        
        # Z axis - Blue
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 15)
        glEnd()

    def draw_toolpath(self):
        """Draw all geometry segments."""
        for segment in self.geometry_segments:
            self.draw_segment(segment)

    def draw_segment(self, segment):
        """Draw a single geometry segment."""
        # Check if this segment should be highlighted
        is_highlighted = segment.line_number in self.highlighted_lines
        
        # Set colors and line style based on move type
        if segment.move_type == MoveType.RAPID:
            if not self.show_rapid:
                return
            color = (1.0, 1.0, 0.0) if is_highlighted else (0.0, 0.8, 0.2)
            self.draw_dashed_line(segment.start_point, segment.end_point, color)
            
        elif segment.move_type == MoveType.FEED:
            if not self.show_feed:
                return
            color = (1.0, 1.0, 0.0) if is_highlighted else (0.2, 0.5, 1.0)
            self.draw_solid_line(segment.start_point, segment.end_point, color)
            
        elif segment.move_type in [MoveType.ARC_CW, MoveType.ARC_CCW]:
            if not self.show_arcs:
                return
            color = (1.0, 1.0, 0.0) if is_highlighted else (1.0, 0.5, 0.2)
            self.draw_arc(segment, color)

    def draw_solid_line(self, start, end, color):
        """Draw a solid line between two points."""
        glLineWidth(2.5)
        glColor3f(*color)
        
        glBegin(GL_LINES)
        glVertex3f(start.x, start.y, start.z)
        glVertex3f(end.x, end.y, end.z)
        glEnd()

    def draw_dashed_line(self, start, end, color):
        """Draw a dashed line for rapid moves."""
        glLineWidth(2.0)
        glColor3f(*color)
        
        glLineStipple(1, 0xAAAA)
        glEnable(GL_LINE_STIPPLE)
        
        glBegin(GL_LINES)
        glVertex3f(start.x, start.y, start.z)
        glVertex3f(end.x, end.y, end.z)
        glEnd()
        
        glDisable(GL_LINE_STIPPLE)

    def draw_arc(self, segment, color):
        """Draw an arc segment using tessellation."""
        if not segment.center_point or segment.radius is None:
            # Fallback to straight line
            self.draw_solid_line(segment.start_point, segment.end_point, color)
            return
        
        glLineWidth(2.5)
        glColor3f(*color)
        
        # Get arc parameters
        start = segment.start_point
        end = segment.end_point
        center = segment.center_point
        
        # Determine plane and calculate angles
        if segment.plane == 'XY':
            start_angle = math.atan2(start.y - center.y, start.x - center.x)
            end_angle = math.atan2(end.y - center.y, end.x - center.x)
        elif segment.plane == 'XZ':
            start_angle = math.atan2(start.z - center.z, start.x - center.x)
            end_angle = math.atan2(end.z - center.z, end.x - center.x)
        elif segment.plane == 'YZ':
            start_angle = math.atan2(start.z - center.z, start.y - center.y)
            end_angle = math.atan2(end.z - center.z, end.y - center.y)
        else:
            # Default to XY
            start_angle = math.atan2(start.y - center.y, start.x - center.x)
            end_angle = math.atan2(end.y - center.y, end.x - center.x)
        
        # Handle direction
        if segment.move_type == MoveType.ARC_CW:
            if end_angle >= start_angle:
                end_angle -= 2 * math.pi
        else:  # CCW
            if end_angle <= start_angle:
                end_angle += 2 * math.pi
        
        # Tessellate arc
        angle_diff = end_angle - start_angle
        num_segments = max(8, int(abs(angle_diff) * 180 / math.pi / 5))
        
        glBegin(GL_LINE_STRIP)
        for i in range(num_segments + 1):
            fraction = i / num_segments
            angle = start_angle + angle_diff * fraction
            
            if segment.plane == 'XY':
                x = center.x + segment.radius * math.cos(angle)
                y = center.y + segment.radius * math.sin(angle)
                z = start.z + (end.z - start.z) * fraction
            elif segment.plane == 'XZ':
                x = center.x + segment.radius * math.cos(angle)
                y = start.y + (end.y - start.y) * fraction
                z = center.z + segment.radius * math.sin(angle)
            elif segment.plane == 'YZ':
                x = start.x + (end.x - start.x) * fraction
                y = center.y + segment.radius * math.cos(angle)
                z = center.z + segment.radius * math.sin(angle)
            else:
                x = center.x + segment.radius * math.cos(angle)
                y = center.y + segment.radius * math.sin(angle)
                z = start.z + (end.z - start.z) * fraction
            
            glVertex3f(x, y, z)
        glEnd()

    def mousePressEvent(self, event):
        """Handle mouse press for camera control."""
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse movement for camera rotation."""
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()

        if event.buttons() & Qt.LeftButton:
            self.x_rot += dy * 0.5
            self.z_rot += dx * 0.5
        elif event.buttons() & Qt.RightButton:
            # Could add panning here
            pass

        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y() / 120.0
        self.zoom += delta * 2.0
        self.update()

    def toggle_display_option(self, option):
        """Toggle display options."""
        if option == 'rapid':
            self.show_rapid = not self.show_rapid
        elif option == 'feed':
            self.show_feed = not self.show_feed
        elif option == 'arcs':
            self.show_arcs = not self.show_arcs
        elif option == 'grid':
            self.show_grid = not self.show_grid
        elif option == 'axes':
            self.show_axes = not self.show_axes
        
        self.update()

    def reset_view(self):
        """Reset camera to default position."""
        self.zoom = -30.0
        self.x_rot = -30.0
        self.y_rot = 0.0
        self.z_rot = 30.0
        self.update()