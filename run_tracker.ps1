# PowerShell script to run GPS BLE tracker continuously
Write-Host "Starting GPS BLE Tracker loop..."
Write-Host "Press Ctrl+C to stop the script"

while ($true) {
    try {
        # Run the Python script with 10 second duration
        Write-Host "`nStarting new tracking session..."
        python python/gps_ble_tracker.py  --gps-port COM29 --ble-port COM28 --duration 10 --log-level info
        
        # Wait for 1 second before next execution
        Write-Host "Waiting 1 second before next session..."
        Start-Sleep -Seconds 1
        
    } catch {
        Write-Host "An error occurred: $_"
        Start-Sleep -Seconds 5  # Wait 5 seconds before retrying if there's an error
    }
} 