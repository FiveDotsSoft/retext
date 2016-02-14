# This file is part of ReText
# Copyright: 2016 Maurice van der Pot
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtCore import QPoint

class SyncScroll:

    def __init__(self, previewFrame,
                       editorPositionToSourceLineFunc,
                       sourceLineToEditorPositionFunc):
        self.posmap = {}
        self.frame = previewFrame
        self.editorPositionToSourceLine = editorPositionToSourceLineFunc
        self.sourceLineToEditorPosition = sourceLineToEditorPositionFunc

        self.lastPreviewPosition = QPoint()

        self.editorViewportHeight = 0
        self.editorViewportOffset = 0
        self.editorCursorPosition = 0

        previewFrame.contentsSizeChanged.connect(self._handlePreviewResized)

    def handleEditorResized(self, editorViewportHeight):
        self.editorViewportHeight = editorViewportHeight
        self._updatePreviewScrollPosition()

    def handleEditorScrolled(self, editorViewportOffset):
        self.editorViewportOffset = editorViewportOffset
        return self._updatePreviewScrollPosition()

    def handleCursorPositionChanged(self, editorCursorPosition):
        self.editorCursorPosition = editorCursorPosition
        return self._updatePreviewScrollPosition()

    def _handlePreviewResized(self):
        self._recalculatePositionMap()
        self._updatePreviewScrollPosition()

    def linearScale(self, fromValue, fromMin, fromMax, toMin, toMax):
        fromRange = fromMax - fromMin
        toRange = toMax - toMin

        toValue = toMin

        if fromRange:
            toValue += ((fromValue - fromMin) * toRange) / float(fromRange)

        return toValue

    def _updatePreviewScrollPosition(self):
        if not self.posmap:
            return

        textedit_pixel_to_scroll_to = self.editorCursorPosition

        if textedit_pixel_to_scroll_to < self.editorViewportOffset:
            textedit_pixel_to_scroll_to = self.editorViewportOffset

        last_viewport_pixel = self.editorViewportOffset + self.editorViewportHeight
        if textedit_pixel_to_scroll_to > last_viewport_pixel:
            textedit_pixel_to_scroll_to = last_viewport_pixel

        line_to_scroll_to = self.editorPositionToSourceLine(textedit_pixel_to_scroll_to)

        # Do a binary search through the posmap to find the nearest line above
        # and below the line to scroll to for which the rendered position is
        # known.
        posmap_lines = [0] + sorted(self.posmap.keys())
        min_index = 0
        max_index = len(posmap_lines) - 1
        while max_index - min_index > 1:
            current_index = int((min_index + max_index) / 2)
            if posmap_lines[current_index] > line_to_scroll_to:
                max_index = current_index
            else:
                min_index = current_index

        # number of nearest line above and below for which we have a position
        min_line = posmap_lines[min_index]
        max_line = posmap_lines[max_index]

        min_textedit_pos = self.sourceLineToEditorPosition(min_line)
        max_textedit_pos = self.sourceLineToEditorPosition(max_line)

        # rendered pixel position of nearest line above and below
        min_preview_pos = self.posmap[min_line]
        max_preview_pos = self.posmap[max_line]

        # calculate rendered pixel position of line corresponding to cursor
        # (0 == top of document)
        preview_pixel_to_scroll_to = self.linearScale(textedit_pixel_to_scroll_to,
                                                      min_textedit_pos, max_textedit_pos,
                                                      min_preview_pos, max_preview_pos)

        distance_to_top_of_viewport = textedit_pixel_to_scroll_to - self.editorViewportOffset
        preview_scroll_offset = preview_pixel_to_scroll_to - distance_to_top_of_viewport

        self.lastPreviewPosition = self.frame.scrollPosition()
        self.lastPreviewPosition.setY(preview_scroll_offset)
        self.frame.setScrollPosition(self.lastPreviewPosition)

    def _recalculatePositionMap(self):
        # Create a list of input line positions mapped to vertical pixel positions in the preview
        self.posmap = {}
        elements = self.frame.findAllElements('[data-posmap]')

        if elements:
            # If there are posmap attributes, then build a posmap
            # dictionary from them that will be used whenever the
            # cursor is moved.
            for el in elements:
                value = el.attribute('data-posmap', 'invalid')
                bottom = el.geometry().bottom()

                # Ignore data-posmap entries that do not have integer values
                try:
                    self.posmap[int(value)] = bottom
                except ValueError:
                    pass

            self.posmap[0] = 0
