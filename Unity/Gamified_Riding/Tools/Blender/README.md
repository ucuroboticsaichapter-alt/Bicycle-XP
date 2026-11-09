# Stylized bicycle source

Run from the project root using the installed Blender 5.x executable:

```powershell
& 'D:/Blender_5/blender.exe' --background --factory-startup --python Tools/Blender/generate_stylized_bicycle.py
```

The generator requires no add-ons, network access, textures, or Unity packages.

Outputs:

- `ArtSource/Bicycle/Bicycle_Stylized.blend`: complete authoring hierarchy and a separate studio preview scene, outside Unity Assets.
- `Assets/Models/Bicycle_Stylized.fbx`: export meshes and pivot empties only.
- `Temp/BicycleReview/Blender_ThreeQuarter.png`: studio render.
- `Temp/BicycleReview/Bicycle_Report.json`: measured dimensions, pivots, and triangle count.

Measured model size: 1.804 m long, 1.081 m high, 0.726 m wide at the handlebars; 11,512 triangles in 12 mesh assemblies. Seven shared surface materials are remapped to the `Bike_*.mat` URP/Lit assets in `Assets/Materials`.

FBX export uses metres, -Z forward / Y up, unit scaling, baked space transform, and no animation, subdivision, lights, or cameras. Export-only flattening avoids Blender's nested-pivot axis-bake bug. The `.blend` keeps the original hierarchy. In Unity the model faces +Z, Y is up, and all imported mesh transforms have identity rotation and unit scale. Wheel local X axes run through their axles.

`Assets/Prefabs/Bicycle_Stylized.prefab` reconnects the named assemblies: Chainring and Crank_Left/Right under Crankset, Pedal_Left/Right under their respective crank arms. Shared mesh references still come from the FBX. Regenerating the FBX preserves named source assemblies; the Unity prefab retains the logical hierarchy and URP remaps. Unity ModelImporter settings: global scale 1, use file scale, bakeAxisConversion false (basis already baked by Blender), imported normals, no tangents, no mesh compression, no animation, no cameras/lights, no colliders, read/write disabled.

The root is on the ground below the saddle. SampleScene's Bicycle_Visual compensates the rider parent's horizontal scale, preserving metre dimensions. Its vertical offset aligns the lowest tire tread with the existing road surface. No gameplay scripts or animation controllers belong to this visual asset. The rider's original MeshRenderer alone is disabled; its collider, movement, telemetry, and follow-camera target are preserved.
