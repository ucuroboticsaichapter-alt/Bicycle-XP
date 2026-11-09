using UnityEngine;

/// <summary>
/// Rolls the existing wheel visuals from signed world displacement.
/// Independent of input, speed telemetry, and the source of bicycle movement.
/// </summary>
[DisallowMultipleComponent]
[AddComponentMenu("Gamified Riding/Bicycle Wheel Animator")]
public sealed class BicycleWheelAnimator : MonoBehaviour
{
    [SerializeField, Tooltip("Transform moved by the cycling controller. No input is read here.")]
    private Transform movementSource;

    [SerializeField, Tooltip("Stable bicycle heading; do not assign a spinning wheel.")]
    private Transform bicycleForward;

    [Header("Existing Wheel Visuals")]
    [SerializeField] private Transform frontWheel;
    [SerializeField] private Transform rearWheel;

    [SerializeField, Min(0.001f), Tooltip("World-space rolling radius in metres, measured from the tire/tread geometry.")]
    private float frontWheelRadius = 0.352f;

    [SerializeField, Min(0.001f), Tooltip("World-space rolling radius in metres, measured from the tire/tread geometry.")]
    private float rearWheelRadius = 0.352f;

    [SerializeField, Tooltip("Signed axle axis in the front wheel's local space. Verified as +X for this model.")]
    private Vector3 frontLocalAxle = Vector3.right;

    [SerializeField, Tooltip("Signed axle axis in the rear wheel's local space. Verified as +X for this model.")]
    private Vector3 rearLocalAxle = Vector3.right;

    private Transform sampledSource;
    private Vector3 previousPosition;

    private void OnEnable()
    {
        ResetDisplacementSample();
    }

    private void LateUpdate()
    {
        if (movementSource == null)
        {
            sampledSource = null;
            return;
        }

        // Rebinding or enabling establishes a baseline instead of adding a jump.
        if (sampledSource != movementSource)
        {
            ResetDisplacementSample();
            return;
        }

        Vector3 currentPosition = movementSource.position;
        Vector3 displacement = currentPosition - previousPosition;
        previousPosition = currentPosition;

        Transform heading = bicycleForward != null ? bicycleForward : transform;
        float distance = Vector3.Dot(displacement, heading.forward);
        if (distance == 0f)
        {
            return;
        }

        RotateWheel(frontWheel, frontWheelRadius, frontLocalAxle, distance);
        if (rearWheel != frontWheel)
        {
            RotateWheel(rearWheel, rearWheelRadius, rearLocalAxle, distance);
        }
    }

    /// <summary>Call after an intentional teleport to avoid rolling across the jump.</summary>
    public void ResetDisplacementSample()
    {
        sampledSource = movementSource;
        if (movementSource != null)
        {
            previousPosition = movementSource.position;
        }
    }

    private static void RotateWheel(Transform wheel, float radius, Vector3 localAxle, float distance)
    {
        if (wheel == null || radius <= 0f || localAxle.sqrMagnitude < 0.0001f)
        {
            return;
        }

        // Distance already integrates movement over time; no deltaTime or speed
        // multiplier belongs here. Local multiplication retains the axle pivot.
        float degrees = distance / radius * Mathf.Rad2Deg;
        wheel.localRotation *= Quaternion.AngleAxis(degrees, localAxle.normalized);
    }
}
