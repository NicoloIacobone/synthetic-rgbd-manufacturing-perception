"""Blender side of the IR stereo renders (M3). Import only inside Blender (scripts/bproc.sh).

- Projector: a Blender SPOT light (point source, radius 0, cone 180 deg, shadows on) whose
  emission is the dot pattern of synthrgbd.projector, mapped over the field of projection
  (A-36) with the texel conventions documented there. BlenderProc's `setup_as_projector` is not
  used: it copies the camera pose (no offset from the left imager) and the camera FOV, turns
  shadows off, and loads the pattern into an 8-bit sRGB image (values would be linearised).
- IR camera pair: left imager = the BOP camera pose; right imager = +baseline along the camera x
  axis (OpenCV/Blender x right), same orientation (rectified). Both are rendered `pad` px wider on
  the left (cx + pad, same f, A-40), interleaved as frames L0, R0, L1, R1, ...
- Output: linear radiance from OpenEXR (float32, view transform not applied), no denoiser, no
  adaptive sampling, no sample clamping (A-32), green channel (grey materials, white light).
"""

import bpy
import blenderproc as bproc
import numpy as np


def _diffuse_lobe(material) -> "bpy.types.ShaderNodeBsdfDiffuse":
    """Principled -> Add Shader <- Diffuse BSDF -> Material Output, created once per material and reused, so
    the metal pass can carry the Lambertian term of the S-16 fit and the matte pass can switch it off."""
    nt = material.blender_obj.node_tree
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeBsdfDiffuse" and n.name == "ir_diffuse_lobe":
            return n
    principled = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.name = "ir_diffuse_lobe"
    add = nt.nodes.new("ShaderNodeAddShader")
    for link in list(out.inputs["Surface"].links):
        nt.links.remove(link)
    nt.links.new(principled.outputs["BSDF"], add.inputs[0])
    nt.links.new(diff.outputs["BSDF"], add.inputs[1])
    nt.links.new(add.outputs["Shader"], out.inputs["Surface"])
    return diff


def matte(material, albedo: float) -> None:
    """Lambertian-like Principled BSDF (metallic 0, no specular layer); the extra diffuse lobe, if any, is off."""
    material.set_principled_shader_value("Base Color", [albedo, albedo, albedo, 1.0])
    material.set_principled_shader_value("Metallic", 0.0)
    material.set_principled_shader_value("Roughness", 1.0)
    material.set_principled_shader_value("Specular IOR Level", 0.0)
    for n in material.blender_obj.node_tree.nodes:
        if n.name == "ir_diffuse_lobe":
            n.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)


def metal(material, base: float, roughness: float, diffuse: float = 0.0) -> None:
    """IR metal for the C3 pass (A-11): GGX metal (Principled, metallic 1, grey base colour = normal-incidence
    reflectance at 850 nm, Cycles roughness with alpha = roughness^2) plus a Lambertian lobe of albedo
    `diffuse`, as in the GGX + Lambertian fit of [S-16]."""
    material.set_principled_shader_value("Base Color", [base, base, base, 1.0])
    material.set_principled_shader_value("Metallic", 1.0)
    material.set_principled_shader_value("Roughness", roughness)
    material.set_principled_shader_value("Specular IOR Level", 0.5)    # the default; matte() sets 0 (extra passes run after it)
    d = _diffuse_lobe(material)
    d.inputs["Color"].default_value = (diffuse, diffuse, diffuse, 1.0)
    d.inputs["Roughness"].default_value = 0.0


def ir_render_settings(ir_cfg: dict) -> None:
    r = ir_cfg["ir_render"]
    bproc.renderer.set_denoiser(None)
    bproc.renderer.set_max_amount_of_samples(r["samples"])
    sc = bpy.context.scene
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.sample_clamp_direct = r["clamp"]
    sc.cycles.sample_clamp_indirect = r["clamp"]
    # BlenderProc's defaults are glossy 0 and max 3; glossy 0 removes every reflected image from metal (A-57).
    if r.get("glossy_bounces") is not None:
        sc.cycles.glossy_bounces = r["glossy_bounces"]
    if r.get("max_bounces") is not None:
        sc.cycles.max_bounces = r["max_bounces"]
    bproc.renderer.set_world_background([r["ambient"]] * 3, strength=1.0)
    bproc.renderer.set_output_format(file_format="OPEN_EXR", color_depth=32, view_transform="Standard")


def make_projector(pattern: np.ndarray, fov_deg, power_w: float) -> "bproc.types.Light":
    """Spot light projecting `pattern` (float, row 0 = top of the field) over fov_deg = (H, V)."""
    light = bproc.types.Light(light_type="SPOT", name="ir_projector")
    light.set_energy(power_w)
    data = light.blender_obj.data
    data.spot_size = np.pi
    data.spot_blend = 0.0
    data.shadow_soft_size = 0.0
    data.use_nodes = True
    nt = data.node_tree
    nodes, links = nt.nodes, nt.links

    H, W = pattern.shape
    img = bpy.data.images.new("dot_pattern", width=W, height=H, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((H, W, 4), dtype=np.float32)
    rgba[..., :3] = np.flipud(pattern)[..., None]          # Blender rows start at the bottom
    img.pixels.foreach_set(rgba.ravel())

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "CLIP"
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["Normal"], sep.inputs["Vector"])
    # Light local frame: forward = -Z, x right, y up. tx = X / (-Z), ty_up = Y / (-Z);
    # u = 0.5 + tx / Fx, v = 0.5 + ty_up / Fy (v = 0 at the bottom row).
    fx = 2 * np.tan(np.deg2rad(fov_deg[0]) / 2)
    fy = 2 * np.tan(np.deg2rad(fov_deg[1]) / 2)

    def math(op, a, b):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for i, x in enumerate((a, b)):
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = float(x)
            else:
                links.new(x, n.inputs[i])
        return n.outputs[0]

    negz = math("MULTIPLY", sep.outputs["Z"], -1.0)
    u = math("ADD", math("DIVIDE", math("DIVIDE", sep.outputs["X"], negz), fx), 0.5)
    v = math("ADD", math("DIVIDE", math("DIVIDE", sep.outputs["Y"], negz), fy), 0.5)
    comb = nodes.new("ShaderNodeCombineXYZ")
    links.new(u, comb.inputs["X"])
    links.new(v, comb.inputs["Y"])
    links.new(comb.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], nodes["Emission"].inputs["Color"])
    return light


def add_ir_frames(T_left_list, baseline_m: float, proj_x_m: float, light, K_ext: np.ndarray, W_ext: int, H: int,
                  energies=None) -> int:
    """Replace all keyframes by the interleaved IR frames (L0, R0, L1, R1, ...); key the projector
    (left pose + proj_x along camera x) and optionally its energy per left view. Returns #frames."""
    bproc.utility.reset_keyframes()
    bproc.camera.set_intrinsics_from_K_matrix(K_ext, W_ext, H)
    frame = 0
    for i, T in enumerate(T_left_list):
        T = np.asarray(T, dtype=np.float64)
        for side in (0.0, baseline_m):
            Tc = T.copy()
            Tc[:3, 3] = T[:3, 3] + T[:3, 0] * side
            bproc.camera.add_camera_pose(Tc, frame)
            light.set_location(T[:3, 3] + T[:3, 0] * proj_x_m, frame)
            light.set_rotation_mat(T[:3, :3], frame)
            if energies is not None:
                light.set_energy(float(energies[i]), frame)
            frame += 1
    return frame


def render_ir() -> list:
    """Render all frames; returns per-frame float32 radiance (H, W_ext) (green channel)."""
    # Own output key/prefix: BlenderProc refuses a second "colors" entry with another file type
    # (the RGB pass of the same session writes rgb_*.png).
    data = bproc.renderer.render(file_prefix="ir_", output_key="ir", load_keys={"ir"})
    return [np.asarray(c, dtype=np.float32)[..., 1] for c in data["ir"]]


def extended_K(K: np.ndarray, pad: int) -> np.ndarray:
    Ke = np.array(K, dtype=np.float64)
    Ke[0, 2] += pad
    return Ke
