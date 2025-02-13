from dataclasses import dataclass, astuple
import numpy as np
import qt
import vtk
from collections import OrderedDict
import logging


@dataclass
class Color:
  r: float
  g: float
  b: float


@dataclass
class Point:
  x: float
  y: float
  z: float


@dataclass
class TagInfo:
  tagName: str
  tagType: int  # 1 = Branch point  2 = Free Edge point 3 = Interior point  4 = others
  tagColor: Color
  tagIndex: int  # anatomical index
  mrmlNodeID: str = ""


@dataclass
class LabelTriangle:
  labelName: str
  labelColor: str
  mrmlNodeID: str = ""


@dataclass
class TagTriangle:
  p1: Point
  p2: Point
  p3: Point
  id1: int  # index in global point array
  id2: int
  id3: int
  seq1: int # vertex index in skeleton
  seq2: int
  seq3: int
  index: int # the triangle label index

  @property
  def triPtIds(self):
    return [self.id1, self.id2, self.id3]

  @property
  def centerPos(self):
    return np.array([astuple(self.p1), astuple(self.p2), astuple(self.p3)]).mean(axis=0)


@dataclass
class TagPoint:
  pos: Point
  radius: float   # TODO: this could be calculated upon request
  typeIndex: int  # tag index
  comboBoxIndex: int  # index in combobox
  seq: int  # the sequence in all vertices  on skeleton


@dataclass
class TagEdge:
  ptId1: int
  ptId2: int
  constrain: int
  numEdge: int
  seq: int

  def increaseNumEdges(self):
    self.numEdge += 1

  def decreaseNumEdges(self):
    self.numEdge -= 1

  @property
  def edgPtIds(self):
    return [self.ptId1, self.ptId2]


class CustomInformation(object):

  def getEdgeConstraint(self, tagPoint1: TagPoint, tagPoint2: TagPoint) -> int:
    type1 = self.vectorTagInfo[tagPoint1.comboBoxIndex].tagType
    type2 = self.vectorTagInfo[tagPoint2.comboBoxIndex].tagType

    # 1 = Branch point  2 = Free Edge point 3 = Interior point  4 = others
    if type1 == 1 and type2 == 1:  # branch points
      return 3
    elif type1 == 2 and type2 == 2:  # edge points
      return 1
    elif type1 == 3 and type2 == 3:  # interior points
      return 2
    elif (type1 == 1 and type2 == 2) or (type1 == 2 and type2 == 1):  # branch point and edge point
      return 2
    elif (type1 == 1 and type2 == 3) or (type1 == 3 and type2 == 1):  # branch point and interior point
      return 2
    elif (type1 == 2 and type2 == 3) or (type1 == 3 and type2 == 2):  # edge point and interior point
      return 2

  def __init__(self, polydata=None):
    self.polydata = polydata

    self.labelData = list()

    self.vectorTagInfo = list()
    self.vectorLabelInfo = list()
    self.vectorTagTriangles = list()
    self.vectorTagPoints = list()
    self.vectorTagEdges = OrderedDict()

  def hasCustomData(self):
    return len(self.vectorTagInfo) > 0

  def __repr__(self):
    return f"TagInfo: \n\t{self.vectorTagInfo}\n\n" + \
           f"LabelInfo: \n\t{self.vectorLabelInfo}\n\n" + \
           f"TagTriangles: \n\t{self.vectorTagTriangles}\n\n" + \
           f"TagPoints: \n\t{self.vectorTagPoints}\n\n" + \
           f"TagEdges: \n\t{self.vectorTagEdges}\n\n" + \
           f"LabelData: \n\t{self.labelData}"

  def readCustomData(self):
    fielddata = self.polydata.GetFieldData()

    self._readCustomDataLabel(fielddata)
    self._readCustomDataTag(fielddata)
    self._readCustomDataPoints(fielddata)
    self._readCustomDataTriLabel(fielddata)
    self._readCustomDataTri(fielddata)
    self._readCustomDataEdge(fielddata)

  def _readCustomDataLabel(self, fielddata):
    # TODO: not required
    self.labelData = []

    labelDBL = fielddata.GetArray("Label")
    if not labelDBL:
      return

    logging.debug(f"Label size {labelDBL.GetNumberOfValues()}")

    for i in range(labelDBL.GetNumberOfValues()):
      self.labelData.append(labelDBL.GetValue(i))

  def _readCustomDataTag(self, fielddata):
    self.vectorTagInfo = list()

    tagDBL = fielddata.GetArray("TagInfo")
    tagStr = fielddata.GetAbstractArray("TagName")

    if not tagStr:
      return

    logging.debug(f"string size {tagStr.GetNumberOfValues()}")

    j = 0
    for i in range(0, tagDBL.GetNumberOfValues() - 1, 5):
      info = TagInfo(
        tagType=int(tagDBL.GetValue(i)),
        tagIndex=int(tagDBL.GetValue(i + 1)),
        tagColor=Color(tagDBL.GetValue(i + 2), tagDBL.GetValue(i + 3), tagDBL.GetValue(i + 4)),
        tagName=tagStr.GetValue(j)
      )
      self.vectorTagInfo.append(info)
      j += 1

  def _readCustomDataPoints(self, fielddata):
    self.vectorTagPoints = list()
    ptsDBL = fielddata.GetArray("TagPoints")
    if not ptsDBL:
      return

    for i in range(0, ptsDBL.GetNumberOfValues(), 7):
      tagPt = TagPoint(
        pos=Point(ptsDBL.GetValue(i), ptsDBL.GetValue(i + 1), ptsDBL.GetValue(i + 2)),
        radius=ptsDBL.GetValue(i + 3),
        seq=int(ptsDBL.GetValue(i + 4)),
        typeIndex=int(ptsDBL.GetValue(i + 5)),
        comboBoxIndex=int(ptsDBL.GetValue(i + 6))
      )
      self.vectorTagPoints.append(tagPt)

  def _readCustomDataTriLabel(self, fielddata):
    self.vectorLabelInfo = list()

    tagTriDBL = fielddata.GetArray("LabelTriangleColor")
    tagTriStr = fielddata.GetAbstractArray("LabelTriangleName")
    if not tagTriStr:
      return

    logging.debug(f"label triangle size {tagTriStr.GetNumberOfValues()}")

    j = 0
    for i in range(0, tagTriDBL.GetNumberOfValues(), 3):
      lt = LabelTriangle(
        labelName=tagTriStr.GetValue(j),
        labelColor=str(qt.QColor(tagTriDBL.GetValue(i), tagTriDBL.GetValue(i + 1), tagTriDBL.GetValue(i + 2)))
      )

      self.vectorLabelInfo.append(lt)

      j += 1

  def _readCustomDataTri(self, fielddata):
    self.vectorTagTriangles = list()
    triDBL = fielddata.GetArray("TagTriangles")
    if not triDBL:
      return

    for i in range(0, triDBL.GetNumberOfValues(), 16):
      tri = TagTriangle(
        p1=Point(triDBL.GetValue(i), triDBL.GetValue(i + 1), triDBL.GetValue(i + 2)),
        id1=int(triDBL.GetValue(i + 3)),
        seq1=int(triDBL.GetValue(i + 4)),
        p2=Point(triDBL.GetValue(i + 5), triDBL.GetValue(i + 6), triDBL.GetValue(i + 7)),
        id2=int(triDBL.GetValue(i + 8)),
        seq2=int(triDBL.GetValue(i + 9)),
        p3=Point(triDBL.GetValue(i + 10), triDBL.GetValue(i + 11), triDBL.GetValue(i + 12)),
        id3=int(triDBL.GetValue(i + 13)),
        seq3=int(triDBL.GetValue(i + 14)),
        index=int(triDBL.GetValue(i + 15))
      )

      self.vectorTagTriangles.append(tri)

  def _readCustomDataEdge(self, fielddata):
    self.vectorTagEdges = OrderedDict()
    edgeDBL = fielddata.GetArray("TagEdges")
    if not edgeDBL:
      return

    for i in range(0, edgeDBL.GetNumberOfValues(), 5):
      edge = TagEdge(
        ptId1=int(edgeDBL.GetValue(i)),
        ptId2=int(edgeDBL.GetValue(i + 1)),
        seq=int(edgeDBL.GetValue(i + 2)),
        numEdge=int(edgeDBL.GetValue(i + 3)),
        constrain=int(edgeDBL.GetValue(i + 4))
      )
      if any(val != 0 for val in astuple(edge)):
        self.vectorTagEdges[i//5] = edge


class CustomInformationWriter(object):

  @property
  def vectorTagTriangles(self):
      return self.data.vectorTagTriangles

  @property
  def vectorTagInfo(self):
      return self.data.vectorTagInfo

  @property
  def vectorLabelInfo(self):
      return self.data.vectorLabelInfo

  @property
  def vectorTagPoints(self):
      return self.data.vectorTagPoints

  @property
  def vectorTagEdges(self):
      return self.data.vectorTagEdges

  @property
  def labelData(self):
      return self.data.labelData

  def __init__(self, data: CustomInformation):
    self.data = data

  def writeCustomData(self, polydata):
    finalPolyData = vtk.vtkPolyData()
    finalPolyData.DeepCopy(polydata)
    fielddata = finalPolyData.GetFieldData()

    self._writeCustomDataLabel(fielddata)
    self._writeCustomDataTag(fielddata)
    self._writeCustomDataPoints(fielddata)
    self._writeCustomDataTriLabel(fielddata)
    self._writeCustomDataTri(fielddata)
    self._writeCustomDataEdge(fielddata)

    finalPolyData.SetFieldData(fielddata)
    return finalPolyData

  def writeCustomDataToFile(self, outputFilePath):
    finalPolyData = self.writeCustomData(self.data.polydata)
    writer = vtk.vtkGenericDataObjectWriter()
    writer.SetFileName(outputFilePath)
    writer.SetInputData(finalPolyData)
    writer.Update()
    writer.Write()

  def _writeCustomDataLabel(self, fielddata):
    if fielddata.GetArray("Label"):
      fielddata.RemoveArray("Label")

    import numpy as np
    labelData = np.zeros((self.data.polydata.GetNumberOfPoints(),), dtype=float)
    for pt in self.vectorTagPoints:
      labelData[pt.seq] = pt.typeIndex

    fltArray1 = vtk.vtkFloatArray()
    fltArray1.SetName("Label")
    for label in labelData:
      fltArray1.InsertNextValue(label)
    if len(labelData) != 0:
      fielddata.AddArray(fltArray1)


  def _writeCustomDataTag(self, fielddata):
    if fielddata.GetArray("TagInfo"):
      fielddata.RemoveArray("TagInfo")
    if fielddata.GetArray("TagName"):
      fielddata.RemoveArray("TagName")

    fltArray5 = vtk.vtkFloatArray()
    fltArray5.SetName("TagInfo")
    strArray1 = vtk.vtkStringArray()
    strArray1.SetName("TagName")
    for i in range(len(self.vectorTagInfo)):
      fltArray5.InsertNextValue(self.vectorTagInfo[i].tagType)
      fltArray5.InsertNextValue(self.vectorTagInfo[i].tagIndex)
      fltArray5.InsertNextValue(self.vectorTagInfo[i].tagColor.r)
      fltArray5.InsertNextValue(self.vectorTagInfo[i].tagColor.g)
      fltArray5.InsertNextValue(self.vectorTagInfo[i].tagColor.b)

      strArray1.InsertNextValue(self.vectorTagInfo[i].tagName)
    if len(self.vectorTagInfo) != 0:
      fielddata.AddArray(fltArray5)
      fielddata.AddArray(strArray1)

  def _writeCustomDataTriLabel(self, fielddata):
    if fielddata.GetArray("LabelTriangleName"):
      fielddata.RemoveArray("LabelTriangleName")
    if fielddata.GetArray("LabelTriangleColor"):
      fielddata.RemoveArray("LabelTriangleColor")

    strArray2_1 = vtk.vtkStringArray()
    strArray2_1.SetName("LabelTriangleName")
    fltArray2_1 = vtk.vtkFloatArray()
    fltArray2_1.SetName("LabelTriangleColor")
    for i in range(len(self.vectorLabelInfo)):
      strArray2_1.InsertNextValue(self.vectorLabelInfo[i].labelName)
      qc = qt.QColor(self.vectorLabelInfo[i].labelColor)
      fltArray2_1.InsertNextValue(qc.red())
      fltArray2_1.InsertNextValue(qc.green())
      fltArray2_1.InsertNextValue(qc.blue())
    if len(self.vectorLabelInfo) != 0:
      fielddata.AddArray(strArray2_1)
      fielddata.AddArray(fltArray2_1)

  def _writeCustomDataPoints(self, fielddata):
    if fielddata.GetArray("TagPoints"):
      fielddata.RemoveArray("TagPoints")

    fltArray4 = vtk.vtkFloatArray()
    fltArray4.SetName("TagPoints")
    for i in range(len(self.vectorTagPoints)):
      fltArray4.InsertNextValue(self.vectorTagPoints[i].pos.x)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].pos.y)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].pos.z)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].radius)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].seq)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].typeIndex)
      fltArray4.InsertNextValue(self.vectorTagPoints[i].comboBoxIndex)
    if len(self.vectorTagPoints) != 0:
      fielddata.AddArray(fltArray4)

  def _writeCustomDataEdge(self, fielddata):
    if fielddata.GetArray("TagEdges"):
      fielddata.RemoveArray("TagEdges")
    fltArray3 = vtk.vtkFloatArray()
    fltArray3.SetName("TagEdges")

    # create dummy array to fill in vtk fields
    from SyntheticSkeletonLib.Utils import pairNumber
    maxId = pairNumber(len(self.vectorTagPoints), len(self.vectorTagPoints))
    import numpy as np
    vectorTagEdges = np.zeros((maxId+1,), dtype=TagEdge)
    for key, val in self.vectorTagEdges.items():
      vectorTagEdges[key] = val

    for i in range(len(vectorTagEdges)):
      edge = vectorTagEdges[i]
      if not edge:
        for j in range(5):
          fltArray3.InsertNextValue(0)
      else:
        fltArray3.InsertNextValue(edge.ptId1)
        fltArray3.InsertNextValue(edge.ptId2)
        fltArray3.InsertNextValue(edge.seq)
        fltArray3.InsertNextValue(edge.numEdge)
        fltArray3.InsertNextValue(edge.constrain)
    if len(vectorTagEdges) != 0:
      fielddata.AddArray(fltArray3)

  def _writeCustomDataTri(self, fielddata):
    if fielddata.GetArray("TagTriangles"):
      fielddata.RemoveArray("TagTriangles")

    fltArray2 = vtk.vtkFloatArray()
    fltArray2.SetName("TagTriangles")
    for i in range(len(self.vectorTagTriangles)):
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p1.x)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p1.y)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p1.z)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].id1)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].seq1)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p2.x)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p2.y)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p2.z)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].id2)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].seq2)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p3.x)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p3.y)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].p3.z)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].id3)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].seq3)
      fltArray2.InsertNextValue(self.vectorTagTriangles[i].index)
    if len(self.vectorTagTriangles) != 0:
      fielddata.AddArray(fltArray2)
