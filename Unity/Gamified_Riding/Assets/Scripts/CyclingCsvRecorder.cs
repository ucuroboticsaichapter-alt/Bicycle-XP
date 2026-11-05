using System;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

[RequireComponent(typeof(BasicCyclingMovement))]
public class CyclingCsvRecorder : MonoBehaviour
{
    private BasicCyclingMovement movement;
    private StreamWriter writer;
    private string filePath;
    private double sessionStartTime;
    private double nextSampleTime = 1d;
    private bool sessionEnded;

    private void Start()
    {
        movement = GetComponent<BasicCyclingMovement>();
        sessionStartTime = Time.realtimeSinceStartupAsDouble;
        nextSampleTime = 1d;
        sessionEnded = false;

        try
        {
            string directory = Path.Combine(Application.persistentDataPath, "CyclingLogs");
            Directory.CreateDirectory(directory);
            string timestamp = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff", CultureInfo.InvariantCulture);
            filePath = Path.Combine(directory, $"cycling_{timestamp}_{Guid.NewGuid():N}.csv");
            writer = new StreamWriter(new FileStream(filePath, FileMode.CreateNew, FileAccess.Write,
                FileShare.Read), new UTF8Encoding(false));
            writer.WriteLine("utc_timestamp,elapsed_session_time_s,riding_time_s,speed_kmh,distance_m,input_source");
            writer.Flush();
            Debug.Log($"Cycling CSV telemetry: {filePath}", this);
        }
        catch (Exception exception)
        {
            HandleWriteFailure(exception);
        }
    }

    private void LateUpdate()
    {
        if (writer == null || sessionEnded)
        {
            return;
        }

        double elapsed = Time.realtimeSinceStartupAsDouble - sessionStartTime;
        if (elapsed >= nextSampleTime)
        {
            WriteSample(elapsed);
            nextSampleTime = Math.Floor(elapsed) + 1d;
        }
    }

    private void WriteSample(double elapsed)
    {
        try
        {
            writer.WriteLine(string.Format(CultureInfo.InvariantCulture,
                "{0},{1:F3},{2:F3},{3:F3},{4:F3},keyboard_simulated",
                DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture), elapsed,
                movement.RidingTimeSeconds, movement.CurrentSpeedKmh, movement.TotalDistanceMetres));
            writer.Flush();
        }
        catch (Exception exception)
        {
            HandleWriteFailure(exception);
        }
    }

    private void OnApplicationQuit()
    {
        EndSession();
    }

    private void OnDestroy()
    {
        EndSession();
    }

    private void EndSession()
    {
        if (sessionEnded || writer == null)
        {
            return;
        }

        sessionEnded = true;
        WriteSample(Time.realtimeSinceStartupAsDouble - sessionStartTime);
        CloseWriter();
    }

    private void HandleWriteFailure(Exception exception)
    {
        Debug.LogWarning($"Cycling CSV recording stopped for '{filePath}': {exception.Message}", this);
        CloseWriter();
    }

    private void CloseWriter()
    {
        StreamWriter writerToClose = writer;
        writer = null;
        try
        {
            writerToClose?.Dispose();
        }
        catch (Exception exception)
        {
            Debug.LogWarning($"Could not close cycling CSV '{filePath}': {exception.Message}", this);
        }
    }
}
