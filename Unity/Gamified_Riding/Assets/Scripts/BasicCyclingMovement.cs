using UnityEngine;
using UnityEngine.InputSystem;

public class BasicCyclingMovement : MonoBehaviour
{
    private const float Speed = 3f;
    private const float MinimumZ = -25f;
    private const float MaximumZ = 27f;

    private float currentSpeedKmh;
    private float totalDistanceMetres;
    private float ridingTimeSeconds;

    public float CurrentSpeedKmh => currentSpeedKmh;
    public float TotalDistanceMetres => totalDistanceMetres;
    public float RidingTimeSeconds => ridingTimeSeconds;

    private void Update()
    {
        currentSpeedKmh = 0f;
        Keyboard keyboard = Keyboard.current;
        if (Time.deltaTime <= 0f || keyboard == null ||
            (!keyboard.wKey.isPressed && !keyboard.upArrowKey.isPressed))
        {
            return;
        }

        Vector3 position = transform.position;
        float previousZ = position.z;
        position.z = Mathf.Clamp(position.z + Speed * Time.deltaTime, MinimumZ, MaximumZ);
        transform.position = position;

        float distanceMoved = Mathf.Abs(transform.position.z - previousZ);
        currentSpeedKmh = distanceMoved / Time.deltaTime * 3.6f;
        totalDistanceMetres += distanceMoved;
        if (distanceMoved > 0f)
        {
            ridingTimeSeconds += Mathf.Min(Time.deltaTime, distanceMoved / Speed);
        }
    }

    private void OnGUI()
    {
        GUI.Box(new Rect(12f, 12f, 280f, 112f), "Cycling Telemetry (Debug)");
        GUI.Label(new Rect(24f, 40f, 256f, 72f),
            $"Speed: {currentSpeedKmh:F1} km/h\n" +
            $"Distance: {totalDistanceMetres:F2} m\n" +
            $"Riding time: {ridingTimeSeconds:F2} s");
    }
}
