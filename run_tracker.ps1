# PowerShell script to run GPS BLE tracker continuously
Write-Host "Iniciando bucle del tracker GPS BLE..."
Write-Host "Presione Ctrl+C para detener el script"

while ($true) {
    try {
        # Run the Python script with 10 second duration
        Write-Host "`nIniciando nueva sesión de rastreo..."
        python python/gps_ble_tracker.py --gps-port COM29 --ble-port COM28 --duration 10 --log-level info
        
        # Wait for 1 second before next execution
        Write-Host "Esperando 1 segundo antes de la siguiente sesión..."
        Start-Sleep -Seconds 1
        
    } catch {
        Write-Host "Ocurrió un error: $_"
        Start-Sleep -Seconds 5  # Wait 5 seconds before retrying if there's an error
    }
} 