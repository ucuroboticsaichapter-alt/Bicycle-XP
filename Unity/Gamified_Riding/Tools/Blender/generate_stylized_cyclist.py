"""V4.2 static cyclist. Run with Blender 5.x --background --python this_file.

Reads the existing bicycle .blend as a fitting reference, never rebuilds it.
All design/contact coordinates are metres in the bicycle's Unity-local basis:
X right, Y up, Z forward. No animation, armature modifiers, or collider geometry.
"""
import bpy
import math
import json
import hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BIKE = ROOT / 'ArtSource/Bicycle/Bicycle_Stylized.blend'
SOURCE = ROOT / 'ArtSource/Cyclist/Cyclist_Stylized.blend'
FBX = ROOT / 'Assets/Models/Cyclist_Stylized.fbx'
REPORT = ROOT / 'ArtSource/Cyclist/Cyclist_Fit_Report.json'
REVIEW = ROOT / 'Temp/CyclistReview'
for d in (SOURCE.parent, FBX.parent, REVIEW):
    d.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BIKE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.data.scenes['Bicycle_Model']
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
collection = bpy.data.collections.new('Cyclist_Export')
scene.collection.children.link(collection)

def p(v):
    return Vector((-v[0], -v[2], v[1]))

def u(v):
    return Vector((-v[0], v[2], -v[1]))

def source_vertices(obj, mat_name=None):
    ids = set()
    for poly in obj.data.polygons:
        if mat_name is None or obj.data.materials[poly.material_index].name == mat_name:
            ids.update(poly.vertices)
    return [u(obj.matrix_world @ obj.data.vertices[i].co) for i in ids]

def midpoint(points):
    return Vector(tuple((min(v[i] for v in points)+max(v[i] for v in points))*.5 for i in range(3)))

# Actual grip rubber, upper saddle hull, and pedal platform bounds from the
# previously authored bicycle. Do not infer these from its overall dimensions.
bar_vertices = source_vertices(bpy.data.objects['Handlebar_and_Controls'], 'Bike_Graphite_Rubber')
grips = {}
pedals = {}
for side, sign in (('Left', -1), ('Right', 1)):
    grips[side] = midpoint([v for v in bar_vertices if v.x*sign > .235 and v.y > 1.01])
    pv = source_vertices(bpy.data.objects['Pedal_'+side])
    # Axle extends inward; the outer platform, rather than axle midpoint,
    # defines the shoe's ball-of-foot contact point.
    platform = [v for v in pv if v.x*sign > .125]
    pedals[side] = midpoint(platform)
    pedals[side].y = max(v.y for v in platform)
saddle_vertices = source_vertices(bpy.data.objects['Saddle_Assembly'], 'Bike_Graphite_Rubber')
saddle_y = max(v.y for v in saddle_vertices)
seat_contact = Vector((0, saddle_y, -.01))
contacts = {'Saddle':seat_contact,
            'Grip_Left':grips['Left'], 'Grip_Right':grips['Right'],
            'Pedal_Left':pedals['Left'], 'Pedal_Right':pedals['Right']}

def material(name, rgb):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = .7
    return m

JERSEY = material('Cyclist_Jersey_Teal', (.025,.39,.38))
FABRIC = material('Cyclist_Dark_Fabric', (.035,.055,.072))
SKIN = material('Cyclist_Warm_Skin', (.49,.255,.135))
LIGHT_SKIN = material('Cyclist_Skin_Highlight', (.64,.36,.20))
CORAL = bpy.data.materials['Bike_Warm_Coral']
CREAM = bpy.data.materials['Bike_Cream']
MATERIALS = [JERSEY,FABRIC,SKIN,LIGHT_SKIN,CORAL,CREAM]

upper_body_mapping = False

def relaxed_spine(v):
    """Keep the seat/waist fixed; ease the shoulder girdle down and forward."""
    v = Vector(v)
    t = max(0.0, min(1.0, (v.y-1.16)/(.315)))
    t = t*t*(3-2*t)
    return v + Vector((0, -.025*t, .035*t))

def shape_point(v):
    return relaxed_spine(v) if upper_body_mapping else Vector(v)

def mesh(name, vertices, faces, mat):
    data=bpy.data.meshes.new(name+'_Mesh')
    data.from_pydata([p(shape_point(v)) for v in vertices], [], faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    collection.objects.link(obj)
    data.materials.append(mat)
    return obj

def loft(name, rings, mat, sides=12):
    """Sculpted horizontal cross sections: (center, half-width, half-depth)."""
    vv=[]
    for center,rx,rz in rings:
        center=Vector(center)
        for i in range(sides):
            a=i*math.tau/sides
            vv.append(center+Vector((math.cos(a)*rx,0,math.sin(a)*rz)))
    ff=[]
    for j in range(len(rings)-1):
        for i in range(sides):
            ff.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    ff += [tuple(reversed(range(sides))),tuple(range((len(rings)-1)*sides,len(rings)*sides))]
    return mesh(name,vv,ff,mat)

def limb(name,a,b,sections,mat,sides=10):
    """Anatomically shaped elliptical rings along a joint-to-joint axis."""
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    right=Vector((1,0,0));right=(right-axis*right.dot(axis)).normalized()
    depth=axis.cross(right).normalized()
    vv=[]
    for t,rx,rd in sections:
        center=a.lerp(b,t)
        for i in range(sides):
            theta=i*math.tau/sides
            vv.append(center+right*math.cos(theta)*rx+depth*math.sin(theta)*rd)
    ff=[]
    for j in range(len(sections)-1):
        for i in range(sides):
            ff.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    ff += [tuple(reversed(range(sides))),tuple(range((len(sections)-1)*sides,len(sections)*sides))]
    return mesh(name,vv,ff,mat)

def ribbon(name, coords, width, mat):
    vv=[]
    for x,y,z in coords:
        vv.extend([(x-width*.5,y,z),(x+width*.5,y,z)])
    ff=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(coords)-1)]
    return mesh(name,vv,ff,mat)

def joint_solve(a,b,l1,l2,pole):
    a,b=Vector(a),Vector(b);delta=b-a;d=delta.length
    assert abs(l1-l2)+.001 < d < l1+l2-.002, (d,l1,l2)
    direction=delta/d
    normal=Vector(pole)-direction*Vector(pole).dot(direction)
    normal.normalize()
    along=(l1*l1-l2*l2+d*d)/(2*d)
    return a+direction*along+normal*math.sqrt(max(0,l1*l1-along*along))

def empty(name,pos=(0,0,0),parent=None):
    obj=bpy.data.objects.new(name,None);collection.objects.link(obj)
    obj.location=p(pos)
    bpy.context.view_layer.update()
    if parent:
        world=obj.matrix_world.copy();obj.parent=parent
        obj.matrix_parent_inverse=parent.matrix_world.inverted();obj.matrix_world=world
    return obj

def finish(parts,name,pivot,parent):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    if len(parts)>1:bpy.ops.object.join()
    obj=bpy.context.object;obj.name=name
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    scene.cursor.location=p(shape_point(pivot));bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    old=list(obj.data.materials);unique=list(dict.fromkeys(old));remap=[unique.index(m) for m in old]
    slots=[remap[face.material_index] for face in obj.data.polygons]
    obj.data.materials.clear()
    for m in unique:obj.data.materials.append(m)
    for face,slot in zip(obj.data.polygons,slots):face.material_index=slot;face.use_smooth=False
    bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=parent
    obj.matrix_parent_inverse=parent.matrix_world.inverted();obj.matrix_world=world
    return obj

root=empty('Cyclist_Stylized')
hip=Vector((0,saddle_y+.089,-.025))
pelvis=finish([loft('Padded_Riding_Shorts',[
    ((0,saddle_y+.002,-.02),.065,.065),
    ((0,saddle_y+.026,-.025),.125,.105),
    ((0,hip.y-.005,-.025),.155,.117),
    ((0,hip.y+.066,.005),.142,.10)],FABRIC),
    loft('Waistband', [((0,hip.y+.058,.004),.143,.101),((0,hip.y+.073,.014),.143,.10)],JERSEY)],'Pelvis',hip,root)

waist=Vector((0,hip.y+.055,.012))
upper_body_mapping = True
torso_parts=[loft('Sculpted_Jersey',[
    (waist,.142,.10),((0,1.23,.055),.151,.105),((0,1.33,.116),.175,.115),
    ((0,1.405,.183),.197,.117),((0,1.47,.225),.195,.105),((0,1.51,.25),.155,.085)],JERSEY)]
torso_parts.append(loft('Coral_Jersey_Chest_Band',[
    ((0,1.327,.117),.176,.117),((0,1.357,.142),.187,.12)],CORAL))
torso_parts.append(loft('Cream_Jersey_Piping',[
    ((0,1.359,.144),.188,.12),((0,1.366,.15),.190,.12)],CREAM))
torso_parts.append(limb('Neck',(0,1.494,.248),(0,1.637,.30),[(0,.049,.045),(.5,.047,.045),(1,.047,.045)],SKIN))
torso_parts.append(loft('Jersey_Collar',[((0,1.502,.25),.064,.055),((0,1.535,.266),.059,.05)],FABRIC))
torso_parts.append(ribbon('Front_Zip',[(0,1.18,.130),(0,1.23,.161),(0,1.32,.225),(0,1.405,.301),(0,1.475,.330)],.009,CREAM))
torso=finish(torso_parts,'Torso',waist,pelvis)

head_parts=[loft('Sculpted_Head',[
    ((0,1.603,.326),.043,.040),((0,1.63,.338),.062,.057),
    ((0,1.68,.341),.080,.076),((0,1.735,.334),.086,.087),
    ((0,1.79,.33),.082,.087),((0,1.83,.32),.065,.07),((0,1.85,.31),.032,.043)],SKIN)]
for sign in (-1,1):
    head_parts.append(loft('Ear', [((sign*.084,1.692,.315),.013,.018),
                                  ((sign*.092,1.728,.318),.017,.025),
                                  ((sign*.087,1.756,.322),.010,.016)],LIGHT_SKIN,8))
    x=sign*.033
    head_parts.append(mesh('Almond_Eye',[(x-.020,1.738,.418),(x-.012,1.748,.424),(x+.015,1.747,.423),(x+.022,1.737,.418),(x+.010,1.730,.421),(x-.013,1.730,.421)],[(0,1,2,3,4,5)],CREAM))
    head_parts.append(mesh('Pupil',[(x-.006,1.733,.426),(x-.006,1.744,.427),(x+.005,1.744,.427),(x+.006,1.733,.426)],[(0,1,2,3)],FABRIC))
    head_parts.append(mesh('Brow',[(x-.022,1.760,.417),(x-.018,1.769,.418),(x+.018,1.766,.419),(x+.022,1.758,.418)],[(0,1,2,3)],FABRIC))
head_parts.append(mesh('Angular_Nose',[(-.013,1.736,.419),(.013,1.736,.419),(.017,1.697,.417),(-.017,1.697,.417),(0,1.707,.462)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],LIGHT_SKIN))
head_parts.append(mesh('Smile',[(-.025,1.668,.402),(-.014,1.660,.410),(.014,1.660,.410),(.025,1.668,.402),(.014,1.655,.409),(-.014,1.655,.409)],[(0,1,2,3,4,5)],FABRIC))
head_parts.append(mesh('Smile_Teeth',[(-.015,1.665,.411),(.015,1.665,.411),(.010,1.661,.412),(-.010,1.661,.412)],[(0,1,2,3)],CREAM))
head=finish(head_parts,'Head',(0,1.61,.30),torso)

helmet_parts=[loft('Faceted_Helmet_Shell',[
    ((0,1.786,.31),.094,.106),((0,1.814,.305),.111,.130),
    ((0,1.867,.300),.108,.133),((0,1.915,.29),.073,.100),((0,1.937,.28),.015,.025)],JERSEY),
    loft('Helmet_Dark_Rim',[((0,1.783,.31),.095,.107),((0,1.800,.308),.103,.118)],FABRIC),
    loft('Coral_Helmet_Band',[((0,1.808,.305),.111,.131),((0,1.828,.303),.113,.134)],CORAL)]
for x in (-.058,0,.058):
    helmet_parts.append(ribbon('Cream_Helmet_Ridge',[(x,1.824,.431),(x*.94,1.887,.401),(x*.7,1.934,.29),(x*.9,1.881,.19),(x,1.827,.178)],.014,CREAM))
for sign in (-1,1):
    for j in range(2):
        x=sign*(.026+j*.043)
        helmet_parts.append(ribbon('Recessed_Helmet_Vent',[(x,1.853,.421),(x*.9,1.906,.377),(x*.75,1.935,.305)],.019,FABRIC))
    helmet_parts.append(limb('Chin_Strap',(sign*.092,1.793,.30),(sign*.058,1.615,.357),[(0,.006,.004),(1,.006,.004)],FABRIC,4))
helmet_parts.append(mesh('Small_Helmet_Visor',[(-.091,1.808,.397),(.091,1.808,.397),(.082,1.800,.473),(-.082,1.800,.473),(-.078,1.812,.464),(.078,1.812,.464)],[(0,1,2,3),(0,4,5,1),(3,2,5,4)],CORAL))
helmet=finish(helmet_parts,'Helmet',(0,1.61,.30),head)
upper_body_mapping = False

joints={}
limb_lengths={}
for side,sign in (('Left',-1),('Right',1)):
    shoulder=relaxed_spine(Vector((sign*.182,1.475,.235)))
    grip=grips[side]
    wrist=grip+Vector((-sign*.010,.052,-.061))
    # The elbow pole lies mostly down/back, rather than far out to either side.
    # Wrist/grip contact and both arm lengths remain unchanged.
    elbow=joint_solve(shoulder,wrist,.302,.285,(sign*.18,-.65,-.40))
    upper_parts=[limb('Upper_Arm_Skin',shoulder,elbow,[(0,.053,.054),(.25,.057,.060),(.55,.049,.051),(1,.040,.041)],SKIN)]
    upper_parts.append(limb('Jersey_Sleeve',shoulder,elbow,[(0,.063,.065),(.25,.066,.067),(.48,.059,.060)],JERSEY))
    upper_parts.append(limb('Sleeve_Cuff',shoulder,elbow,[(.45,.060,.061),(.49,.059,.060)],CORAL))
    upper_parts.append(limb('Cream_Sleeve_Trim',shoulder,elbow,[(.49,.059,.060),(.515,.058,.059)],CREAM))
    upper_parts.append(loft('Sculpted_Elbow_Joint',[(elbow+Vector((0,-.042,0)),.013,.015),
        (elbow+Vector((0,-.023,0)),.037,.038),(elbow+Vector((0,.014,0)),.043,.043),
        (elbow+Vector((0,.041,0)),.016,.017)],SKIN,10))
    upper=finish(upper_parts,'Upper_Arm_'+side,shoulder,torso)
    lower=finish([limb('Sculpted_Forearm',elbow,wrist,[(0,.040,.042),(.23,.046,.048),(.53,.038,.039),(1,.025,.029)],SKIN)],'Lower_Arm_'+side,elbow,upper)
    palm=grip+Vector((0,.038,-.008))
    hand_parts=[limb('Glove_Palm',wrist,palm+Vector((0,0,.036)),[(0,.026,.020),(.40,.039,.022),(.75,.040,.022),(1,.033,.018)],FABRIC,10),
                limb('Glove_Coral_Cuff',wrist,wrist+Vector((0,0,.014)),[(0,.028,.022),(1,.029,.023)],CORAL,8)]
    for finger in range(4):
        fx=grip.x+(finger-1.5)*.017
        coords=[Vector((fx,grip.y+.040,grip.z+.018)),Vector((fx,grip.y+.022,grip.z+.040)),Vector((fx,grip.y-.024,grip.z+.035)),Vector((fx,grip.y-.033,grip.z-.005))]
        for j in range(3):hand_parts.append(limb('Curled_Glove_Finger',coords[j],coords[j+1],[(0,.008,.008),(1,.007,.007)],FABRIC,6))
    hand_parts.append(limb('Thumb',palm+Vector((-sign*.028,-.005,-.008)),grip+Vector((-sign*.045,-.012,.012)),[(0,.012,.012),(1,.011,.010)],FABRIC,7))
    finish(hand_parts,'Hand_'+side,wrist,lower)
    hip_joint=Vector((sign*.102,hip.y,-.025))
    pedal=pedals[side]
    ankle=pedal+Vector((0,.078,-.095))
    knee=joint_solve(hip_joint,ankle,.465,.455,(sign*.28,0,1))
    thigh_parts=[limb('Quadriceps',hip_joint,knee,[(0,.081,.087),(.25,.090,.092),(.55,.078,.084),(.80,.060,.066),(1,.051,.054)],SKIN)]
    thigh_parts.append(limb('Riding_Shorts_Leg',hip_joint,knee,[(0,.087,.095),(.25,.094,.098),(.56,.079,.087),(.66,.071,.078)],FABRIC))
    thigh_parts.append(limb('Shorts_Coral_Hem',hip_joint,knee,[(.63,.074,.081),(.66,.072,.079)],CORAL))
    thigh_parts.append(loft('Sculpted_Knee_Joint',[(knee+Vector((0,-.058,0)),.015,.017),
        (knee+Vector((0,-.027,0)),.047,.052),(knee+Vector((0,.021,0)),.054,.058),
        (knee+Vector((0,.057,0)),.017,.020)],SKIN,10))
    thigh=finish(thigh_parts,'Upper_Leg_'+side,hip_joint,pelvis)
    lower_parts=[limb('Sculpted_Calf',knee,ankle,[(0,.051,.055),(.23,.059,.065),(.42,.059,.070),(.70,.039,.046),(1,.028,.032)],SKIN)]
    lower_parts.append(limb('Dark_Ankle_Sock',knee,ankle,[(.82,.034,.039),(1,.029,.034)],FABRIC))
    lower_parts.append(limb('Cream_Sock_Trim',knee,ankle,[(.82,.035,.040),(.85,.034,.040)],CREAM))
    shin=finish(lower_parts,'Lower_Leg_'+side,knee,thigh)
    # Sole profile around actual pedal top, with the ball directly above pedal.
    x,y,z=pedal
    outline=[(-.037,-.166),(.037,-.166),(.048,-.115),(.050,-.025),(.044,.069),(.028,.092),(-.028,.092),(-.044,.069),(-.050,-.025),(-.048,-.115)]
    vv=[(x+xx,y+yy,z+zz) for yy in (0,.016) for xx,zz in outline]
    ff=[tuple(reversed(range(10))),tuple(range(10,20))]+[(i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10)]
    shoes=[mesh('Cream_Grip_Sole',vv,ff,CREAM)]
    sections=[(-.156,.032,.055),(-.112,.042,.084),(-.065,.047,.088),(.015,.043,.057),(.075,.032,.032),(.088,.010,.024)]
    vv=[]
    for zz,w,h in sections:
        vv += [(x-w,y+.016,z+zz),(x-w*.78,y+h*.82,z+zz),(x-w*.32,y+h,z+zz),(x+w*.32,y+h,z+zz),(x+w*.78,y+h*.82,z+zz),(x+w,y+.016,z+zz)]
    ff=[(j*6+i,j*6+(i+1)%6,(j+1)*6+(i+1)%6,(j+1)*6+i) for j in range(len(sections)-1) for i in range(6)]
    ff += [tuple(reversed(range(6))),tuple(range((len(sections)-1)*6,len(sections)*6))]
    shoes.append(mesh('Sculpted_Riding_Shoe',vv,ff,FABRIC))
    for zz in (-.079,-.045):
        shoes.append(mesh('Coral_Shoe_Fastening',[(x-.037,y+.075,z+zz-.009),(x+.037,y+.075,z+zz-.009),(x+.038,y+.072,z+zz+.009),(x-.038,y+.072,z+zz+.009)],[(0,1,2,3)],CORAL))
    finish(shoes,'Foot_'+side,ankle,shin)
    joints[side]={n:list(v) for n,v in dict(hip=hip_joint,knee=knee,ankle=ankle,shoulder=shoulder,elbow=elbow,wrist=wrist).items()}
    limb_lengths[side]={'thigh':(knee-hip_joint).length,'shin':(ankle-knee).length,'upper_arm':(elbow-shoulder).length,'forearm':(wrist-elbow).length}

anchor_root=empty('Contact_Targets',parent=root)
for name,location in contacts.items():empty(name+'_Contact',location,anchor_root)
bpy.context.view_layer.update()
objects=list(collection.objects)
meshes=[o for o in objects if o.type=='MESH']
corners=[u(o.matrix_world@Vector(v)) for o in meshes for v in o.bound_box]
low=Vector(tuple(min(v[i] for v in corners) for i in range(3)))
high=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
triangles=sum(sum(len(face.vertices)-2 for face in o.data.polygons) for o in meshes)
report={'source_bicycle_sha256':hashlib.sha256(BIKE.read_bytes()).hexdigest(),
        'coordinate_system':'Unity bicycle-local X right, Y up, Z forward; metres',
        'contacts':{k:list(v) for k,v in contacts.items()},'joints':joints,'segment_lengths_m':limb_lengths,
        'dimensions_m':list(high-low),'bounds_min':list(low),'bounds_max':list(high),'triangles':triangles,
        'mesh_count':len(meshes),'materials':[m.name for m in MATERIALS],
        'hierarchy':[{'name':o.name,'parent':o.parent.name if o.parent else None,'pivot':list(u(o.matrix_world.translation))} for o in objects]}
report['posture_refinement'] = {'shoulder_drop_m':.025,'shoulder_forward_m':.035,
    'unchanged_contacts':['saddle','grips','pedals'],'unchanged_lower_body':True,
    'elbow_pole_right':[.18,-.65,-.40]}
assert len(meshes)==16,len(meshes)
assert triangles<10000,triangles
assert all(not o.modifiers for o in meshes)
REPORT.write_text(json.dumps(report,indent=2))

# Known-safe sibling export preserves every separate joint pivot. Reconnect the
# recorded hierarchy in Unity's character prefab, exactly as for the bicycle.
saved=[(o,o.parent,o.matrix_world.copy()) for o in objects if o!=root]
for o,parent,world in saved:o.parent=root;o.matrix_parent_inverse=root.matrix_world.inverted();o.matrix_world=world
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={'EMPTY','MESH'},global_scale=1,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    use_space_transform=True,bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=False,
    add_leaf_bones=False,bake_anim=False,path_mode='AUTO',embed_textures=False)
for o,parent,world in saved:o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted();o.matrix_world=world
bpy.context.view_layer.update()

# Reuse the bicycle's studio scene solely for a contact-fit preview.
studio=bpy.data.scenes['Studio_Preview'];studio.collection.children.link(collection)
bpy.context.window.scene=studio
cam=studio.camera;cam.location=(-3.15,-3.8,2.25)
cam.rotation_euler=(Vector((0,-.30,1.0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=2.55
studio.render.resolution_x=1100;studio.render.resolution_y=1100;studio.render.resolution_percentage=100
studio.cycles.samples=48;studio.render.filepath=str(REVIEW/'Cyclist_ThreeQuarter.png')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE));bpy.ops.render.render(write_still=True)
print('CYCLIST_REPORT '+json.dumps(report))
