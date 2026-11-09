# V4.2 static cyclist

```powershell
& 'D:/Blender_5/blender.exe' --background --factory-startup --python-exit-code 1 --python Tools/Blender/generate_stylized_cyclist.py
```

The generator reads `ArtSource/Bicycle/Bicycle_Stylized.blend` as a reference. It never rebuilds or saves the bicycle source or FBX. Grip rubber, saddle upholstery and pedal-platform vertices supply the contact coordinates; both legs and arms use identical segment lengths and analytic two-segment joint solving.

Outputs:

- `ArtSource/Cyclist/Cyclist_Stylized.blend`: full articulated source hierarchy, bicycle reference, and studio preview.
- `ArtSource/Cyclist/Cyclist_Fit_Report.json`: measured contacts in bicycle-local Unity metres, joint pivots, segment lengths, dimensions, source hash and hierarchy.
- `Assets/Models/Cyclist_Stylized.fbx`: only the cyclist mesh assemblies and contact empties.
- `Temp/CyclistReview/Cyclist_ThreeQuarter.png`: fitting preview.

The refined posed character is approximately 0.67 m wide, 1.76 m high and 0.85 m deep, with 3,592 triangles and 16 separate mesh assemblies. These are posed bounds, not standing anthropometric height. There are no animation clips, runtime modifiers, colliders or rig-driving scripts.

The posture refinement keeps the pelvis, legs, feet, wrists, and all bicycle contacts fixed. The shoulder girdle moves 25 mm down and 35 mm forward through a smoothly curved upper-back adjustment. The elbow pole now points mostly down/back: elbow spread is approximately 0.53 m rather than 0.70 m, with about 70 degrees of flexion. Hip-to-shoulder lean increases from about 35 to 40 degrees. Limb lengths, anatomical joint origins, and all six outfit materials are retained. Static mesh intersection checks found no leg/frame or leg/fork surface crossings; a complete animated pedal cycle still needs separate contact, knee-plane, joint-seam, and clearance validation.

Source materials: Cyclist_Jersey_Teal, Cyclist_Dark_Fabric, Cyclist_Warm_Skin, Cyclist_Skin_Highlight, Bike_Warm_Coral and Bike_Cream. Unity uses six reusable opaque URP/Lit material assets; the latter two are reused from the bicycle. The 47 material sections and thin detail silhouettes should be profiled before a Quest release.

Articulation is a rigid object hierarchy, not a skinned humanoid rig:

```text
Cyclist_Stylized
  Pelvis
    Torso
      Head
        Helmet
      Upper_Arm_Left / Upper_Arm_Right
        Lower_Arm_Left / Lower_Arm_Right
          Hand_Left / Hand_Right
    Upper_Leg_Left / Upper_Leg_Right
      Lower_Leg_Left / Lower_Leg_Right
        Foot_Left / Foot_Right
  Contact_Targets
    Saddle_Contact
    Grip_Left_Contact / Grip_Right_Contact
    Pedal_Left_Contact / Pedal_Right_Contact
```

All limb origins correspond to anatomical joints. Future animation must drive the joint hierarchy and maintain foot and hand contacts; no pedalling cycle has been authored or validated in this milestone. Contact_Targets document the static fit in bicycle coordinates.

As with the bicycle, FBX export temporarily flattens the hierarchy to avoid Blender's nested-pivot space-bake bug. The `.blend` retains the source parenting. `Assets/Prefabs/Cyclist_Stylized.prefab` restores the hierarchy while retaining shared FBX mesh references. Unity's importer uses global scale 1, file scale enabled, already-baked axes (`bakeAxisConversion=false`), imported normals, no tangents, no mesh compression, no imported animations, cameras, lights or colliders, and read/write disabled.

In SampleScene, Cyclist_Visual is a sibling of Bicycle_Visual beneath Rider_Placeholder and copies its local offset and scale compensation. Both assets therefore share the same metre-scale coordinate space and follow the existing controller together. The bicycle pivots, rider collider, telemetry, desktop follow camera, and environment remain unchanged. No XR camera is created.
