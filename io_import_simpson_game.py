bl_info = {
    "name": "Simpsons Game Importer Test",
    "author": "Turk",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "",
    "warning": "",
    "category": "Import-Export",
}

import bpy
import bmesh
import os
import io
import struct
import math
import mathutils
import numpy as np
import re
from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       CollectionProperty
                       )
from bpy_extras.io_utils import ImportHelper

class SimpGameImport(bpy.types.Operator, ImportHelper):
    bl_idname = "custom_import_scene.simpgame"
    bl_label = "Import"
    bl_options = {'PRESET', 'UNDO'}
    filter_glob = StringProperty(
            default="*.preinstanced",
            options={'HIDDEN'},
            )
    filepath = StringProperty(subtype='FILE_PATH',)
    files = CollectionProperty(type=bpy.types.PropertyGroup)
    def draw(self, context):
        pass
    def execute(self, context):
        CurFile = open(self.filepath,"rb")
        CurCollection = bpy.data.collections.new("New Mesh")
        bpy.context.scene.collection.children.link(CurCollection)
    
        tmpRead = CurFile.read()
        mshBytes = re.compile(b"\x33\xEA\x00\x00....\x2D\x00\x02\x1C",re.DOTALL)
        iter = 0
        for x in mshBytes.finditer(tmpRead):
            CurFile.seek(x.end()+4)
            FaceDataOff = int.from_bytes(CurFile.read(4),byteorder='little')
            MeshDataSize = int.from_bytes(CurFile.read(4),byteorder='little')
            MeshChunkStart = CurFile.tell()
            CurFile.seek(0x14,1)
            mDataTableCount = int.from_bytes(CurFile.read(4),byteorder='big')
            mDataSubCount = int.from_bytes(CurFile.read(4),byteorder='big')
            mDataOffsets = []
            for i in range(mDataTableCount):
                CurFile.seek(4,1)
                mDataOffsets.append(int.from_bytes(CurFile.read(4),byteorder='big'))
            mDataSubStart = CurFile.tell()
            for i in range(mDataSubCount):#mDataSubCount
                CurFile.seek(mDataSubStart+i*0xc+8)
                offset = int.from_bytes(CurFile.read(4),byteorder='big')
                chunkHead = CurFile.seek(offset+MeshChunkStart+0xC)
                VertCountDataOff = int.from_bytes(CurFile.read(4),byteorder='big')+MeshChunkStart
                CurFile.seek(VertCountDataOff)
                VertChunkTotalSize = int.from_bytes(CurFile.read(4),byteorder='big')
                VertChunkSize = int.from_bytes(CurFile.read(4),byteorder='big')
                VertCount = int(VertChunkTotalSize/VertChunkSize)
                CurFile.seek(8,1)
                VertexStart = int.from_bytes(CurFile.read(4),byteorder='big')+FaceDataOff+MeshChunkStart
                CurFile.seek(0x14,1)
                FaceCount = int(int.from_bytes(CurFile.read(4),byteorder='big')/2)
                CurFile.seek(4,1)
                FaceStart = int.from_bytes(CurFile.read(4),byteorder='big')+FaceDataOff+MeshChunkStart
                

                CurFile.seek(FaceStart)
                StripList = []
                tmpList = []
                for f in range(FaceCount): 
                    Indice = int.from_bytes(CurFile.read(2),byteorder='big')
                    if Indice == 65535:
                        StripList.append(tmpList.copy())
                        tmpList.clear()
                    else:
                        tmpList.append(Indice)
                FaceTable = []
                for f in StripList:
                    for f2 in strip2face(f):
                        FaceTable.append(f2)
                
                
                VertTable = []
                UVTable = []
                for v in range(VertCount):
                    CurFile.seek(VertexStart+v*VertChunkSize)
                    TempVert = struct.unpack('>fff', CurFile.read(4*3))
                    VertTable.append(TempVert)
                    CurFile.seek(VertexStart+v*VertChunkSize+VertChunkSize-8)
                    TempUV = struct.unpack('>ff', CurFile.read(4*2))
                    UVTable.append((TempUV[0],1-TempUV[1]))
                
                
                #build mesh
                mesh1 = bpy.data.meshes.new("Mesh")
                mesh1.use_auto_smooth = True
                obj = bpy.data.objects.new("Mesh_"+str(iter)+"_"+str(i),mesh1)
                CurCollection.objects.link(obj)
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                mesh = bpy.context.object.data
                bm = bmesh.new()
                for v in VertTable:
                    bm.verts.new((v[0],v[1],v[2]))
                list = [v for v in bm.verts]
                for f in FaceTable:
                    try:
                        bm.faces.new((list[f[0]],list[f[1]],list[f[2]]))
                    except:
                        continue
                bm.to_mesh(mesh)
                
                uv_layer = bm.loops.layers.uv.verify()
                for f in bm.faces:
                    f.smooth=True
                    for l in f.loops:
                        luv = l[uv_layer]
                        try:
                            luv.uv = UVTable[l.vert.index]
                        except:
                            continue
                bm.to_mesh(mesh)
                
                bm.free()
                obj.rotation_euler = (1.5707963705062866,0,0)
            iter += 1
        CurFile.close()
        del CurFile
        return {'FINISHED'}


def strip2face(strip):
    flipped = False
    tmpTable = []
    for x in range(len(strip)-2):
        if flipped:
            tmpTable.append((strip[x+2],strip[x+1],strip[x]))
        else:
            tmpTable.append((strip[x+1],strip[x+2],strip[x]))
        flipped = not flipped
    return tmpTable

def utils_set_mode(mode):
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode=mode, toggle=False)

def menu_func_import(self, context):
    self.layout.operator(SimpGameImport.bl_idname, text="Simpson Game (.rws,dff)")
        
def register():
    bpy.utils.register_class(SimpGameImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
def unregister():
    bpy.utils.unregister_class(SimpGameImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        
if __name__ == "__main__":
    register()