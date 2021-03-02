from __future__ import division

import os
import unittest
from builtins import range

import ctk
import qt
import slicer
import numpy as np

__author__ = 'Alessandro Delmonte'
__email__ = 'delmonte.ale92@gmail.com'


class SeptalCurve:
    def __init__(self, parent):
        parent.title = 'SeptalCurve'
        parent.categories = ['IMAG2']
        parent.dependencies = []
        parent.contributors = ['Alessandro Delmonte (IMAG2)']
        parent.helpText = '''INSERT HELP TEXT.'''
        parent.acknowledgementText = '''Septal curvature and mPAP computation. Not intended for clinical use.'''

        self.parent = parent

        module_dir = os.path.dirname(self.parent.path)
        icon_path = os.path.join(module_dir, 'Resources', 'icon.jpg')
        if os.path.isfile(icon_path):
            parent.icon = qt.QIcon(icon_path)

        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['SeptalCurve'] = self.runTest

    def __repr__(self):
        return 'SeptalCurve(parent={})'.format(self.parent)

    def __str__(self):
        return 'SeptalCurve module initialization class.'

    @staticmethod
    def runTest():
        tester = SeptalCurveTest()
        tester.runTest()


class SeptalCurveWidget:
    def __init__(self, parent=None):
        self.moduleName = self.__class__.__name__
        if self.moduleName.endswith('Widget'):
            self.moduleName = self.moduleName[:-6]
        settings = qt.QSettings()
        try:
            self.developerMode = settings.value('Developer/DeveloperMode').lower() == 'true'
        except AttributeError:
            self.developerMode = settings.value('Developer/DeveloperMode') is True

        self.logic = SeptalCurveLogic()

        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()

        if not parent:
            self.setup()
            self.parent.show()

    def __repr__(self):
        return 'SeptalCurveWidget(parent={})'.format(self.parent)

    def __str__(self):
        return 'SeptalCurve GUI class'

    def setup(self):
        vs_collapsible_button = ctk.ctkCollapsibleButton()
        vs_collapsible_button.text = 'Septal Ratio Computation'

        self.layout.addWidget(vs_collapsible_button)

        vs_form_layout = qt.QFormLayout(vs_collapsible_button)
        vs_form_layout.setVerticalSpacing(13)

        self.markups_selector_septum = slicer.qSlicerSimpleMarkupsWidget()
        self.markups_selector_septum.objectName = 'septumFiducialsNodeSelector'
        self.markups_selector_septum.setNodeBaseName("Septum")
        self.markups_selector_septum.defaultNodeColor = qt.QColor(200, 8, 21)
        self.markups_selector_septum.maximumHeight = 150
        self.markups_selector_septum.markupsSelectorComboBox().noneEnabled = False
        self.markups_selector_septum.connect('markupsFiducialNodeChanged()', self.on_markups_septum_added)
        vs_form_layout.addRow("Septum:", self.markups_selector_septum)
        self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                            self.markups_selector_septum, 'setMRMLScene(vtkMRMLScene*)')

        self.markups_selector_wall = slicer.qSlicerSimpleMarkupsWidget()
        self.markups_selector_wall.objectName = 'lateralwallFiducialsNodeSelector'
        self.markups_selector_wall.setNodeBaseName("LateralWall")
        self.markups_selector_wall.defaultNodeColor = qt.QColor(0, 255, 0)
        self.markups_selector_wall.maximumHeight = 150
        self.markups_selector_wall.markupsSelectorComboBox().noneEnabled = False
        self.markups_selector_wall.connect('markupsFiducialNodeChanged()', self.on_markups_wall_added)
        vs_form_layout.addRow("Lateral Wall:", self.markups_selector_wall)
        self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                            self.markups_selector_wall, 'setMRMLScene(vtkMRMLScene*)')

        groupbox = qt.QGroupBox()
        groupbox.setTitle('Condition:')

        grid_layout = qt.QGridLayout(groupbox)
        grid_layout.setAlignment(3)
        grid_layout.setColumnMinimumWidth(0, 150)
        grid_layout.setColumnMinimumWidth(1, 150)
        grid_layout.setColumnMinimumWidth(2, 150)
        self.radio_baseline = qt.QRadioButton('Baseline')
        self.radio_baseline.setChecked(True)
        self.radio_vasodilation = qt.QRadioButton('Vasodilation')
        grid_layout.addWidget(self.radio_baseline, 0, 0, 0)
        grid_layout.addWidget(self.radio_vasodilation, 0, 1, 0)

        vs_form_layout.addRow(groupbox)

        self.compute_button = qt.QPushButton('Compute Ratio')
        self.compute_button.enabled = True

        self.compute_button.connect('clicked(bool)', self.on_compute_button)
        vs_form_layout.addRow(self.compute_button)

        line = qt.QFrame()
        line.setFrameShape(qt.QFrame().HLine)
        line.setFrameShadow(qt.QFrame().Sunken)
        line.setStyleSheet("min-height: 24px")
        vs_form_layout.addRow(line)

        self.ratio = qt.QLabel()
        font = self.ratio.font
        font.setPointSize(42)
        font.setBold(True)
        self.ratio.setFont(font)
        self.ratio.setText('Septal Ratio = 0')
        vs_form_layout.addRow(self.ratio)

        line = qt.QFrame()
        line.setFrameShape(qt.QFrame().HLine)
        line.setFrameShadow(qt.QFrame().Sunken)
        line.setStyleSheet("min-height: 24px")
        vs_form_layout.addRow(line)

        self.mpap = qt.QLabel()
        self.mpap.setFont(font)
        self.mpap.setText('mPAP = 0')
        vs_form_layout.addRow(self.mpap)

        self.layout.addStretch(1)

        if self.developerMode:

            def createHLayout(elements):
                widget = qt.QWidget()
                rowLayout = qt.QHBoxLayout()
                widget.setLayout(rowLayout)
                for element in elements:
                    rowLayout.addWidget(element)
                return widget

            """Developer interface"""
            self.reloadCollapsibleButton = ctk.ctkCollapsibleButton()
            self.reloadCollapsibleButton.text = "Reload && Test"
            self.layout.addWidget(self.reloadCollapsibleButton)
            reloadFormLayout = qt.QFormLayout(self.reloadCollapsibleButton)

            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "ScriptedLoadableModuleTemplate Reload"
            self.reloadButton.connect('clicked()', self.onReload)

            self.reloadAndTestButton = qt.QPushButton("Reload and Test")
            self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
            self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

            self.editSourceButton = qt.QPushButton("Edit")
            self.editSourceButton.toolTip = "Edit the module's source code."
            self.editSourceButton.connect('clicked()', self.onEditSource)

            self.restartButton = qt.QPushButton("Restart Slicer")
            self.restartButton.toolTip = "Restart Slicer"
            self.restartButton.name = "ScriptedLoadableModuleTemplate Restart"
            self.restartButton.connect('clicked()', slicer.app.restart)

            reloadFormLayout.addWidget(
                createHLayout([self.reloadButton, self.reloadAndTestButton, self.editSourceButton, self.restartButton]))

    def on_markups_septum_added(self):
        displaynode = self.markups_selector_septum.currentNode().GetDisplayNode()
        displaynode.SetTextScale(0)
        displaynode.SetGlyphScale(1.)
        displaynode.SetVisibility(True)

    def on_markups_wall_added(self):
        displaynode = self.markups_selector_wall.currentNode().GetDisplayNode()
        displaynode.SetTextScale(0)
        displaynode.SetGlyphScale(1.)
        displaynode.SetVisibility(True)

    def on_compute_button(self):

        if self.markups_selector_septum.currentNode() and self.markups_selector_wall.currentNode():
            current_seeds_node = self.markups_selector_septum.currentNode()
            septum_init = []
            for n in range(current_seeds_node.GetNumberOfFiducials()):
                current = [0, 0, 0]
                current_seeds_node.GetNthFiducialPosition(n, current)
                septum_init.append(current)
            septum_init = np.array(septum_init)[:3, 1:]

            current_seeds_node = self.markups_selector_wall.currentNode()
            wall_init = []
            for n in range(current_seeds_node.GetNumberOfFiducials()):
                current = [0, 0, 0]
                current_seeds_node.GetNthFiducialPosition(n, current)
                wall_init.append(current)
            wall_init = np.array(wall_init)[:3, 1:]

            ratio, cx = self.logic.compute_ratio(septum_init, wall_init)
            args = {0, 1, 2}
            args_sep = args.difference({np.argmax(septum_init[:, 1]), np.argmin(septum_init[:, 1])}).pop()
            args_wall = args.difference({np.argmax(wall_init[:, 1]), np.argmin(wall_init[:, 1])}).pop()

            if (cx - septum_init[args_sep, 0]) * (septum_init[args_sep, 0] - wall_init[args_wall, 0]) > 0:
                ratio *= -1

            self.ratio.setText('Septal Ratio = {:.2f}'.format(ratio))

            if self.radio_baseline.isChecked():
                mpap = -43.2 * ratio + 42.3
            else:
                mpap = -40.1 * ratio + 41.5

            self.mpap.setText('mPAP = {:.2f}'.format(mpap))

    def onReload(self):
        print('\n' * 2)
        print('-' * 30)
        print('Reloading module: ' + self.moduleName)
        print('-' * 30)
        print('\n' * 2)

        slicer.util.reloadScriptedModule(self.moduleName)

    def onReloadAndTest(self):
        try:
            self.onReload()
            test = slicer.selfTests[self.moduleName]
            test()
        except Exception:
            import traceback
            traceback.print_exc()
            errorMessage = "Reload and Test: Exception!\n\n" + "See Python Console for Stack Trace"
            slicer.util.errorDisplay(errorMessage)

    def onEditSource(self):
        filePath = slicer.util.modulePath(self.moduleName)
        qt.QDesktopServices.openUrl(qt.QUrl("file:///" + filePath, qt.QUrl.TolerantMode))

    def cleanup(self):
        pass


class SeptalCurveLogic:
    def __init__(self):
        pass

    def compute_ratio(self, septum, wall):
        septum_radius, cx_septum = self.define_circle(septum[0, :], septum[1, :], septum[2, :])
        wall_radius, _ = self.define_circle(wall[0, :], wall[1, :], wall[2, :])

        return wall_radius / septum_radius, cx_septum

    @staticmethod
    def define_circle(p1, p2, p3):
        temp = p2[0] * p2[0] + p2[1] * p2[1]
        bc = (p1[0] * p1[0] + p1[1] * p1[1] - temp) / 2.
        cd = (temp - p3[0] * p3[0] - p3[1] * p3[1]) / 2.
        det = (p1[0] - p2[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p2[1])

        if abs(det) < 1.0e-6:
            return np.inf

        cx = (bc * (p2[1] - p3[1]) - cd * (p1[1] - p2[1])) / det
        cy = ((p1[0] - p2[0]) * cd - (p2[0] - p3[0]) * bc) / det

        return np.sqrt((cx - p1[0]) ** 2 + (cy - p1[1]) ** 2), cx


class SeptalCurveTest(unittest.TestCase):

    def __init__(self):
        super(SeptalCurveTest, self).__init__()

    def __repr__(self):
        return 'SeptalCurveTest(). Derived from {}'.format(unittest.TestCase)

    def __str__(self):
        return 'SeptalCurveTest test class'

    def runTest(self, scenario=None):
        pass
