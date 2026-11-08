using UnityEngine;

/// <summary>
/// Desktop prototype chase camera only. An eventual Quest camera must use
/// tracked headset poses rather than this component.
/// </summary>
[DisallowMultipleComponent]
[AddComponentMenu("Gamified Riding/Desktop Follow Camera (Testing Only)")]
public sealed class DesktopFollowCamera : MonoBehaviour
{
    [Header("Desktop Testing Only")]
    [SerializeField, Tooltip("The rider to follow. This component never moves the target.")]
    private Transform followTarget;

    [SerializeField, Tooltip("World-space offset in metres. The current route runs along positive Z.")]
    private Vector3 offset = new Vector3(0f, 2.8f, -6f);

    [SerializeField, Min(0.01f), Tooltip("Position response per second. Higher values follow more closely.")]
    private float followSmoothness = 10f;

    [SerializeField, Min(0.01f), Tooltip("Rotation response per second.")]
    private float rotationSmoothness = 12f;

    [SerializeField, Min(0f), Tooltip("Distance to look ahead along the route's positive Z direction.")]
    private float lookAheadDistance = 3f;

    [SerializeField, Tooltip("Look point height above the rider's pivot, in metres.")]
    private float lookAtHeight = 0.6f;

    private void OnEnable()
    {
        SnapToTarget();
    }

    private void LateUpdate()
    {
        Follow(Time.deltaTime);
    }

    private void Follow(float deltaTime)
    {
        if (followTarget == null || deltaTime <= 0f)
        {
            return;
        }

        float positionBlend = 1f - Mathf.Exp(-Mathf.Max(0.01f, followSmoothness) * deltaTime);
        Vector3 position = Vector3.Lerp(transform.position, followTarget.position + offset, positionBlend);
        Quaternion desiredRotation = GetLookRotation(position);
        Vector3 currentAngles = transform.eulerAngles;
        Vector3 desiredAngles = desiredRotation.eulerAngles;
        float rotationBlend = 1f - Mathf.Exp(-Mathf.Max(0.01f, rotationSmoothness) * deltaTime);

        // Interpolate pitch and yaw separately so the horizon always stays level.
        Quaternion rotation = Quaternion.Euler(
            Mathf.LerpAngle(currentAngles.x, desiredAngles.x, rotationBlend),
            Mathf.LerpAngle(currentAngles.y, desiredAngles.y, rotationBlend),
            0f);
        transform.SetPositionAndRotation(position, rotation);
    }

    [ContextMenu("Snap Desktop Camera To Target")]
    public void SnapToTarget()
    {
        if (followTarget == null)
        {
            return;
        }

        Vector3 position = followTarget.position + offset;
        transform.SetPositionAndRotation(position, GetLookRotation(position));
    }

    private Quaternion GetLookRotation(Vector3 cameraPosition)
    {
        Vector3 lookPoint = followTarget.position +
            Vector3.up * lookAtHeight + Vector3.forward * Mathf.Max(0f, lookAheadDistance);
        Vector3 direction = lookPoint - cameraPosition;

        if (direction.sqrMagnitude < 0.0001f)
        {
            Vector3 angles = transform.eulerAngles;
            return Quaternion.Euler(angles.x, angles.y, 0f);
        }

        // A horizontal look vector supplies a stable yaw even with a vertical offset.
        float horizontalDistance = new Vector2(direction.x, direction.z).magnitude;
        float yaw = horizontalDistance > 0.0001f
            ? Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg
            : transform.eulerAngles.y;
        float pitch = -Mathf.Atan2(direction.y, horizontalDistance) * Mathf.Rad2Deg;
        return Quaternion.Euler(pitch, yaw, 0f);
    }
}
