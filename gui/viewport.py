"""
The OpenGL widget for rendering the 3D toolpath preview.
"""
import math
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *

class Viewport(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commands = []
        self.highlighted_lines = set()

        # Camera state - Corrected initial rotation
        self.zoom = -40.0
        self.x_rot = -60.0  # Changed from 60 to -60 to look from above
        self.y_rot = 0.0
        self.z_rot = 45.0   # Adjusted for a more standard isometric view
        self.last_pos = QPoint()

    def set_path(self, commands):
        """Receives the list of canonical commands from the controller."""
        self.commands = commands
        self.update() # Trigger a repaint

    def highlight_path_segments(self, line_numbers):
        """Receives a set of line numbers to highlight from the main window."""
        self.highlighted_lines = set(line_numbers)
        self.update() # Trigger a repaint

    def initializeGL(self):
        """Called once to set up the OpenGL context."""
        glClearColor(0.1, 0.1, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        """Called whenever the widget is resized."""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h > 0 else 1
        gluPerspective(45, aspect, 0.1, 1000.0)

    def paintGL(self):
        """The main rendering loop."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Apply camera transformations
        glTranslatef(0.0, 0.0, self.zoom)
        glRotatef(self.x_rot, 1.0, 0.0, 0.0)
        glRotatef(self.y_rot, 0.0, 1.0, 0.0)
        glRotatef(self.z_rot, 0.0, 0.0, 1.0)

        self.draw_grid()
        self.draw_axes()
        self.draw_path()

    def draw_grid(self):
        """Draws a simple grid on the XY plane."""
        glLineWidth(1.0)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(-20, 21):
            glVertex3f(i, -20, 0)
            glVertex3f(i, 20, 0)
            glVertex3f(-20, i, 0)
            glVertex3f(20, i, 0)
        glEnd()

    def draw_axes(self):
        """Draws X, Y, Z axes."""
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X Axis (Red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(10, 0, 0)
        # Y Axis (Green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 10, 0)
        # Z Axis (Blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 10)
        glEnd()

    def draw_path(self):
        """Iterates through canonical commands and draws them."""
        if not self.commands:
            return

        glLineWidth(2.5)
        for cmd in self.commands:
            is_highlighted = cmd.source_line_number in self.highlighted_lines
            highlight_color = (1.0, 1.0, 0.0) # Yellow

            if "RapidMove" in str(type(cmd)):
                glColor3f(*highlight_color) if is_highlighted else glColor3f(0.0, 0.8, 0.2) # Green
                glLineStipple(1, 0xAAAA)
                glEnable(GL_LINE_STIPPLE)
                glBegin(GL_LINES)
                glVertex3f(cmd.start_pos['x'], cmd.start_pos['y'], cmd.start_pos['z'])
                glVertex3f(cmd.end_pos['x'], cmd.end_pos['y'], cmd.end_pos['z'])
                glEnd()
                glDisable(GL_LINE_STIPPLE)

            elif "LinearFeed" in str(type(cmd)):
                glColor3f(*highlight_color) if is_highlighted else glColor3f(0.2, 0.5, 1.0) # Blue
                glBegin(GL_LINES)
                glVertex3f(cmd.start_pos['x'], cmd.start_pos['y'], cmd.start_pos['z'])
                glVertex3f(cmd.end_pos['x'], cmd.end_pos['y'], cmd.end_pos['z'])
                glEnd()

            elif "ArcFeed" in str(type(cmd)):
                glColor3f(*highlight_color) if is_highlighted else glColor3f(1.0, 0.5, 0.2) # Orange
                self.draw_arc(cmd)

    def draw_arc(self, cmd):
        """Tessellates an arc into a series of line segments."""
        start = cmd.start_pos
        end = cmd.end_pos
        center = cmd.center

        radius = math.hypot(start['x'] - center['x'], start['y'] - center['y'])
        start_angle = math.atan2(start['y'] - center['y'], start['x'] - center['x'])
        end_angle = math.atan2(end['y'] - center['y'], end['x'] - center['y'])

        if cmd.direction > 0:  # CCW (G3)
            if end_angle <= start_angle:
                end_angle += 2 * math.pi
        else:  # CW (G2)
            if end_angle >= start_angle:
                end_angle -= 2 * math.pi

        angle_diff = end_angle - start_angle
        num_segments = max(10, int(abs(angle_diff) * 180 / math.pi / 5))  # ~5 degrees per segment

        glBegin(GL_LINE_STRIP)
        for i in range(num_segments + 1):
            fraction = i / num_segments
            angle = start_angle + angle_diff * fraction
            x = center['x'] + radius * math.cos(angle)
            y = center['y'] + radius * math.sin(angle)
            z = start['z'] + (end['z'] - start['z']) * fraction
            glVertex3f(x, y, z)
        glEnd()

    # --- Mouse Controls for Camera ---
    def mousePressEvent(self, event: QMouseEvent):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()

        if event.buttons() & Qt.LeftButton:
            self.x_rot += dy
            self.z_rot += dx
        elif event.buttons() & Qt.RightButton:
            # Pan functionality could be added here
            pass

        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() / 120.0
        self.update()

