"""Rebuild with Blender 5.x, no add-ons or external assets required.

  blender --background --factory-startup --python Tools/Blender/generate_stylized_bicycle.py

Design coordinates: X = lateral, Y = forward, Z = up, metres.
Stored Blender geometry faces -Y; FBX -Z forward / Y up maps this to Unity +Z.
The root is on the ground directly below the saddle. Export contains meshes and
named pivot empties only; the separate studio scene is never exported.
"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
bpy.context.preferences.filepaths.save_version = 0
SOURCE = ROOT / 'ArtSource/Bicycle/Bicycle_Stylized.blend'
FBX = ROOT / 'Assets/Models/Bicycle_Stylized.fbx'
REVIEW = ROOT / 'Temp/BicycleReview'
for folder in (SOURCE.parent, FBX.parent, REVIEW):
    folder.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.name = 'Bicycle_Model'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
collection = bpy.data.collections.new('Bicycle_Export')
scene.collection.children.link(collection)

def point(p):
    # FBX/Unity changes handedness: this lateral flip keeps the drive side and
    # named Right pedal on Unity +X, in addition to mapping forward to +Z.
    return Vector((-p[0], -(p[1] + .33), p[2]))

def material(name, color, metallic=0.0, roughness=.55):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return m

TEAL = material('Bike_Deep_Teal', (.025, .32, .34), .18, .4)
CORAL = material('Bike_Warm_Coral', (.95, .25, .17), .05, .46)
RUBBER = material('Bike_Graphite_Rubber', (.035, .045, .052), 0, .88)
METAL = material('Bike_Dark_Metal', (.12, .16, .18), .65, .34)
CREAM = material('Bike_Cream', (.94, .85, .63), .08, .46)
STEEL = material('Bike_Spoke_Steel', (.48, .58, .59), .75, .32)
TREAD = material('Bike_Tread', (.065, .08, .085), 0, .9)
MATERIALS = (TEAL, CORAL, RUBBER, METAL, CREAM, STEEL, TREAD)

def move_to_collection(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)

def empty(name, design_pivot=None, parent=None):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.location = point(design_pivot) if design_pivot is not None else (0, 0, 0)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def mesh_obj(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def tube(name, a, b, radius, mat, sides=10, radius_end=None):
    """Direct mesh tubes, no curve/subdivision modifiers in exported geometry."""
    a, b = point(a), point(b)
    direction = (b-a).normalized()
    u = direction.cross(Vector((0, 0, 1)))
    if u.length < .001:
        u = direction.cross(Vector((0, 1, 0)))
    u.normalize()
    v = direction.cross(u).normalized()
    r2 = radius if radius_end is None else radius_end
    vertices = [center + (u*math.cos(i*math.tau/sides) + v*math.sin(i*math.tau/sides))*r
                for center, r in ((a, radius), (b, r2)) for i in range(sides)]
    faces = [(i, (i+1)%sides, (i+1)%sides+sides, i+sides) for i in range(sides)]
    faces += [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
    return mesh_obj(name, vertices, faces, mat)

def torus_x(name, center, major_radius, minor_radius, mat, major=48, minor=6, width_scale=1):
    cx, cy, cz = center
    vertices = []
    for i in range(major):
        a = i*math.tau/major
        for j in range(minor):
            b = j*math.tau/minor
            r = major_radius + minor_radius*math.cos(b)
            vertices.append(point((cx + minor_radius*math.sin(b)*width_scale,
                                   cy+r*math.sin(a), cz+r*math.cos(a))))
    faces = []
    for i in range(major):
        for j in range(minor):
            faces.append((i*minor+j, ((i+1)%major)*minor+j,
                          ((i+1)%major)*minor+(j+1)%minor, i*minor+(j+1)%minor))
    return mesh_obj(name, vertices, faces, mat)

def block(name, center, dimensions, mat, bevel=.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=point(center))
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj)
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Applied manufacturing chamfer', 'BEVEL')
        mod.width, mod.segments = bevel, 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

def path_tube(name, coords, radius, mat, sides=6):
    return [tube(name + '_' + str(i), a, b, radius, mat, sides)
            for i, (a, b) in enumerate(zip(coords, coords[1:]))]

def finish(parts, name, pivot, parent):
    """One mesh per logical assembly, shared material slots, explicit world pivot."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    scene.cursor.location = point(pivot)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Make all normals outward after mirrored design-coordinate construction.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Compact repeated slots after join to avoid one draw per original tube.
    old = list(obj.data.materials)
    unique = list(dict.fromkeys(old))
    remap = [unique.index(m) for m in old]
    face_slots = [remap[p.material_index] for p in obj.data.polygons]
    obj.data.materials.clear()
    for m in unique:
        obj.data.materials.append(m)
    for polygon, index in zip(obj.data.polygons, face_slots):
        polygon.material_index = index
        polygon.use_smooth = False
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

root = empty('Bicycle_Stylized')
root['description'] = 'Desktop visual only; metres; Unity forward +Z; no colliders or animations'
root['ground_to_saddle_m'] = 1.016
rear = (0, -.55, .355)
front = (0, .55, .355)
bb = (0, -.12, .30)
seat = (0, -.28, .79)
head_low = (0, .41, .69)
head_top = (0, .34, .89)

frame = [tube('Seat_Tube', bb, seat, .026, TEAL),
         tube('Top_Tube', seat, head_top, .027, TEAL),
         tube('Down_Tube', bb, head_low, .034, TEAL, 12),
         tube('Head_Tube', head_low, head_top, .033, TEAL, 12),
         tube('Bottom_Bracket_Shell', (-.055, -.12, .30), (.055, -.12, .30), .034, METAL, 12)]
for sign in (-1, 1):
    axle = (sign*.062, -.55, .355)
    frame += [tube('Chain_Stay', (sign*.039, -.12, .30), axle, .014, TEAL, 8, .010),
              tube('Seat_Stay', (sign*.019, -.28, .76), axle, .012, TEAL, 8, .009),
              tube('Rear_Dropout', (sign*.062, -.55, .355), (sign*.062, -.50, .382), .020, CORAL, 8)]
# Color bands follow the tube axes instead of floating decal planes.
a, b = Vector(bb), Vector(head_low)
for t, length, mat in ((.74, .035, CREAM), (.81, .025, CORAL)):
    frame.append(tube('Down_Tube_Paint_Band', a.lerp(b, t), a.lerp(b, t+length), .0347, mat, 12))
frame += [tube('Seat_Clamp', (0, -.277, .777), (0, -.287, .807), .030, CORAL, 12),
          tube('Headset_Top', (0, .34, .89), (0, .331, .916), .036, METAL, 12),
          tube('Headset_Base', (0, .414, .680), (0, .408, .698), .037, METAL, 12)]
# Compact bottle cage, tucked inside the frame triangle, without a bottle.
frame += path_tube('Bottle_Cage', [(.029, .055, .445), (.055, .10, .48),
                                  (.055, .21, .565), (.029, .235, .58)], .004, METAL, 5)
finish(frame, 'Frame_Assembly', (0, -.33, 0), root)

for name, center in (('Rear_Wheel', rear), ('Front_Wheel', front)):
    _, y, z = center
    wheel = [torus_x('Faceted_Tire', center, .321, .029, RUBBER, 48, 8, 1.10),
             torus_x('Alloy_Rim', center, .298, .013, METAL, 48, 6, 1.0),
             tube('Hub_Barrel', (-.044, y, z), (.044, y, z), .024, METAL, 12),
             tube('Axle', (-.071, y, z), (.071, y, z), .009, STEEL, 8)]
    for side in (-1, 1):
        wheel.append(torus_x('Cream_Rim_Pinstripe', (side*.012, y, z), .304, .0024, CREAM, 48, 4))
        wheel.append(tube('Hub_Flange', (side*.031, y, z), (side*.037, y, z), .038, METAL, 12))
    # Twenty-four laced spokes, alternating hub flange and angular lead.
    for i in range(24):
        a = i*math.tau/24
        h = a + (.22 if i%2 else -.22)
        side = 1 if i%2 else -1
        wheel.append(tube('Laced_Spoke', (side*.033, y+math.sin(h)*.035, z+math.cos(h)*.035),
                          (0, y+math.sin(a)*.292, z+math.cos(a)*.292), .0018, STEEL, 4))
    # Low-profile alternating tread blocks, not oversized toy knobs.
    for i in range(32):
        a = i*math.tau/32
        tread = block('Tread_Block', ((-.011 if i%2 else .011), y+math.sin(a)*.349,
                                     z+math.cos(a)*.349), (.020, .020, .006), TREAD)
        tread.rotation_euler.x = a
        wheel.append(tread)
    # Disc rotor on the left, with six open supporting arms.
    wheel.append(torus_x('Disc_Rotor', (-.048, y, z), .071, .0038, STEEL, 32, 4))
    for i in range(6):
        a = i*math.tau/6
        wheel.append(tube('Rotor_Spider', (-.048, y+math.sin(a)*.021, z+math.cos(a)*.021),
                          (-.048, y+math.sin(a+.24)*.068, z+math.cos(a+.24)*.068), .003, METAL, 5))
    if name == 'Rear_Wheel':
        for i in range(4):
            wheel.append(torus_x('Cassette_Sprocket', (.049+i*.007, y, z), .048-i*.007, .004, METAL, 24, 4))
    obj = finish(wheel, name, center, root)
    obj['future_rotation_axis'] = 'local X; axle-centred pivot'

fork = [tube('Fork_Crown', (-.052, .433, .64), (.052, .433, .64), .027, TEAL, 10)]
for sign in (-1, 1):
    fork += [tube('Fork_Upper', (sign*.051, .433, .652), (sign*.057, .50, .465), .015, STEEL, 10),
             tube('Fork_Lower', (sign*.057, .488, .50), (sign*.065, .55, .355), .022, TEAL, 10, .014),
             tube('Coral_Fork_Cuff', (sign*.057, .488, .50), (sign*.058, .497, .478), .023, CORAL, 10)]
fork.append(block('Front_Brake_Caliper', (-.064, .50, .415), (.027, .047, .036), METAL, .004))
finish(fork, 'Front_Fork', head_top, root)

bars = [tube('Steerer', (0, .333, .913), (0, .307, .995), .016, METAL, 10),
        tube('Stem', (0, .307, .985), (0, .402, 1.025), .019, METAL, 10),
        tube('Bar_Clamp', (-.026, .402, 1.025), (.026, .402, 1.025), .023, CORAL, 10)]
for sign in (-1, 1):
    bars += path_tube('Riser_Bar', [(0, .402, 1.025), (sign*.10, .40, 1.028),
                                  (sign*.20, .357, 1.065), (sign*.35, .32, 1.065)], .012, METAL, 10)
    bars += [tube('Grip', (sign*.245, .346, 1.065), (sign*.35, .32, 1.065), .019, RUBBER, 10),
             tube('Cream_Grip_Collar', (sign*.238, .348, 1.065), (sign*.25, .345, 1.065), .020, CREAM, 10),
             tube('Coral_Bar_End', (sign*.35, .32, 1.065), (sign*.359, .318, 1.065), .0195, CORAL, 10)]
    bars += path_tube('Brake_Lever', [(sign*.223, .36, 1.057), (sign*.218, .412, 1.026),
                                    (sign*.285, .402, 1.018)], .006, METAL, 6)
    bars += path_tube('Brake_Cable', [(sign*.216, .375, 1.044), (sign*.15, .49, .97),
                                    (sign*.08, .48, .86), (sign*.047, .421, .74)], .0026, RUBBER, 5)
finish(bars, 'Handlebar_and_Controls', (0, .34, .89), root)

saddle_parts = [tube('Seat_Post', (0, -.282, .795), (0, -.33, .971), .014, METAL, 10)]
for side in (-1, 1):
    saddle_parts += path_tube('Saddle_Rail', [(side*.025, -.45, .958), (side*.025, -.35, .942),
                                            (side*.025, -.20, .963)], .004, STEEL, 6)
# Upholstered hull with a broad rear, narrow nose and chamfered perimeter.
sections = [(-.49, .058, .986), (-.44, .087, 1.012), (-.34, .081, 1.016),
            (-.25, .043, 1.006), (-.16, .027, .995), (-.145, .015, .982)]
v = []
for y, w, z in sections:
    v += [point((-w*.85,y,z-.037)), point((-w,y,z-.012)), point((-w*.68,y,z)),
          point((w*.68,y,z)), point((w,y,z-.012)), point((w*.85,y,z-.037))]
faces = []
for j in range(len(sections)-1):
    for i in range(6):
        faces.append((j*6+i,j*6+(i+1)%6,(j+1)*6+(i+1)%6,(j+1)*6+i))
faces += [tuple(reversed(range(6))), tuple(range((len(sections)-1)*6,len(sections)*6))]
saddle_parts.append(mesh_obj('Sculpted_Saddle',v,faces,RUBBER))
saddle_parts += [block('Coral_Saddle_Back', (0,-.475,.975), (.11,.018,.014), CORAL, .004),
                 block('Cream_Saddle_Stitch', (0,-.44,1.013), (.095,.008,.004), CREAM, .001)]
finish(saddle_parts, 'Saddle_Assembly', (0,-.33,.96), root)

crank = empty('Crankset', bb, root)
chainring_parts = [torus_x('Chainring_Outer', (.073,-.12,.30), .087,.009,METAL,40,4),
                   tube('Crank_Axle',(-.105,-.12,.30),(.108,-.12,.30),.012,STEEL,10)]
for i in range(5):
    a=i*math.tau/5
    chainring_parts.append(tube('Chainring_Spider',(.073,-.12,.30),(.073,-.12+math.sin(a)*.081,.30+math.cos(a)*.081),.009,METAL,6))
for i in range(32):
    a=i*math.tau/32
    chainring_parts.append(tube('Chainring_Tooth',(.073,-.12+math.sin(a)*.088,.30+math.cos(a)*.088),
                               (.073,-.12+math.sin(a)*.099,.30+math.cos(a)*.099),.0038,STEEL,4))
finish(chainring_parts,'Chainring',bb,crank)
for side, name in ((1,'Right'),(-1,'Left')):
    x=side*.111
    endpoint=(x,-.12+side*.045,.30-side*.159)
    arm=finish([tube('Forged_Crank',(x,-.12,.30),endpoint,.015,METAL,8,.011),
                tube('Crank_Cap',(x-side*.004,-.12,.30),(x+side*.006,-.12,.30),.020,CORAL,10)],
               'Crank_'+name,bb,crank)
    pedal_center=(side*.170,endpoint[1],endpoint[2])
    pedal_parts=[tube('Pedal_Spindle',endpoint,(side*.205,endpoint[1],endpoint[2]),.007,STEEL,8)]
    # Open platform perimeter, with two cross-ribs and cream reflectors.
    px,py,pz=pedal_center
    for sx in (-1,1):
        pedal_parts.append(block('Pedal_Side',(px+sx*.044,py,pz),(.012,.075,.020),METAL,.003))
    for sy in (-1,1):
        pedal_parts.append(block('Pedal_End',(px,py+sy*.032,pz),(.086,.012,.020),CORAL,.003))
        pedal_parts.append(block('Pedal_Reflector',(px,py+sy*.039,pz),(.040,.003,.009),CREAM,.001))
    pedal_parts.append(block('Pedal_Rib',(px,py,pz),(.075,.009,.017),METAL,.002))
    finish(pedal_parts,'Pedal_'+name,(side*.111,endpoint[1],endpoint[2]),arm)

# Continuous chain loop on the drive side, tangential to the two sprockets.
dy,dz=(-.12)-(-.55),.30-.355
distance=math.hypot(dy,dz)
phi=math.atan2(dz,dy)
alpha=math.acos((.096-.048)/distance)
chain_coords=[]
for cy,cz,r,start in ((-.12,.30,.096,phi-alpha),(-.55,.355,.048,phi+alpha)):
    # Front half-circle faces forward; rear half-circle wraps behind the axle.
    for i in range(17):
        a=start + (2*alpha if cy==-.12 else math.tau-2*alpha)*i/16
        chain_coords.append((.083,cy+math.cos(a)*r,cz+math.sin(a)*r))
chain_coords.append(chain_coords[0])
drive=path_tube('Chain_Link_Belt',chain_coords,.0042,STEEL,5)
drive.append(block('Rear_Brake_Caliper',(-.067,-.50,.414),(.025,.045,.033),METAL,.004))
finish(drive,'Drivetrain_and_Chain',(0,-.33,0),root)

# Validate physical scale and bake exported transforms before saving.
bpy.context.view_layer.update()
mesh_objects=[o for o in collection.objects if o.type=='MESH']
corners=[o.matrix_world@Vector(c) for o in mesh_objects for c in o.bound_box]
lo=Vector(tuple(min(v[i] for v in corners) for i in range(3)))
hi=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in mesh_objects)
report={'blender_version':bpy.app.version_string,'source':str(SOURCE),'fbx':str(FBX),
        'dimensions_m':{'width':hi.x-lo.x,'length':hi.y-lo.y,'height':hi.z-lo.z},
        'bounds_blender':[list(lo),list(hi)],'triangles':triangles,
        'mesh_objects':len(mesh_objects),'materials':[m.name for m in MATERIALS],
        'objects':[{ 'name':o.name,'parent':o.parent.name if o.parent else None,
                     'pivot_blender':list(o.matrix_world.translation)} for o in collection.objects]}
assert 1.7<report['dimensions_m']['length']<1.95,report
assert 1.0<report['dimensions_m']['height']<1.2,report
assert triangles<16000,triangles
assert all(not o.modifiers for o in mesh_objects)

bpy.ops.object.select_all(action='DESELECT')
for o in collection.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active=root
# Export the independent animation assemblies as siblings. Blender's FBX space
# bake mishandles nested mesh pivots; keep the proper authoring hierarchy in the
# .blend, and reconnect named assemblies in the Unity visual prefab. No geometry
# or pivot is merged or lost by this export-only flattening.
saved_hierarchy = [(o, o.parent, o.matrix_world.copy()) for o in collection.objects if o != root]
for obj, parent, world in saved_hierarchy:
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()
    obj.matrix_world = world
bpy.context.view_layer.update()
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={'EMPTY','MESH'},
    global_scale=1.0,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=True,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,add_leaf_bones=False,
    bake_anim=False,path_mode='AUTO',embed_textures=False)
for obj, parent, world in saved_hierarchy:
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_world = world
bpy.context.view_layer.update()

# A separate preview scene keeps lighting/cameras/floor out of the exported model.
studio=bpy.data.scenes.new('Studio_Preview')
studio.collection.children.link(collection)
bpy.context.window.scene=studio
studio.render.engine='CYCLES'
studio.cycles.samples=32
studio.cycles.use_denoising=True
studio.render.resolution_x=1200
studio.render.resolution_y=850
studio.render.resolution_percentage=100
studio.world=bpy.data.worlds.new('Studio_World')
studio.world.use_nodes=True
studio.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.21,.24,1)
studio.world.node_tree.nodes['Background'].inputs[1].default_value=.45
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008))
floor=bpy.context.object
floor.name='Studio_Floor_Not_Exported'
floor.data.materials.append(material('Studio_Sand',(.17,.21,.22),0,.8))
def area(name,position,power,size):
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);studio.collection.objects.link(obj);obj.location=position
    obj.rotation_euler=(Vector((0,-.25,.5))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Studio_Key',(2,-1,3),450,3)
area('Studio_Fill',(-2,-1,1.9),250,2.5)
area('Studio_Rim',(0,2,2.5),500,2)
cam_data=bpy.data.cameras.new('Studio_Camera');cam=bpy.data.objects.new('Studio_Camera',cam_data)
studio.collection.objects.link(cam);cam.location=(-2.8,-3.5,1.75)
cam.rotation_euler=(Vector((0,-.33,.56))-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO';cam_data.ortho_scale=2.22;studio.camera=cam
studio.view_settings.view_transform='AgX'
studio.render.filepath=str(REVIEW/'Blender_ThreeQuarter.png')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
bpy.ops.render.render(write_still=True)
(REVIEW/'Bicycle_Report.json').write_text(json.dumps(report,indent=2))
print('BICYCLE_REPORT '+json.dumps(report))
