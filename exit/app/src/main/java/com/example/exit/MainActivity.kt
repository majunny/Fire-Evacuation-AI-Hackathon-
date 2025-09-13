package com.example.exit

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity(), SensorEventListener {

    private lateinit var client: OkHttpClient
    private var webSocket: WebSocket? = null

    private lateinit var statusTextView: TextView
    private lateinit var arrowImageView: ImageView
    private lateinit var directionTextView: TextView

    private val pcLanUrl = "ws://192.168.129.53:8765"
    private val emulatorUrl = "ws://10.0.2.2:8765"

    // Sensor related variables
    private lateinit var sensorManager: SensorManager
    private var rotationVectorSensor: Sensor? = null
    private val rotationMatrix = FloatArray(9)
    private val orientationAngles = FloatArray(3)
    private var currentAzimuth: Float = 0.0f
    private var commandedAzimuth: Float? = null

    private fun isEmulator(): Boolean {
        val f = android.os.Build.FINGERPRINT
        return f.contains("generic") || f.contains("emulator") || f.contains("sdk_gphone")
    }

    private fun getWsUrl(): String = if (isEmulator()) emulatorUrl else pcLanUrl

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusTextView = findViewById(R.id.statusTextView)
        arrowImageView = findViewById(R.id.arrowImageView)
        directionTextView = findViewById(R.id.directionTextView)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        rotationVectorSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)

        client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.SECONDS)
            .pingInterval(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    override fun onStart() {
        super.onStart()
        connectWebSocket()
    }

    override fun onStop() {
        webSocket?.close(1000, "Activity Stopped")
        webSocket = null
        super.onStop()
    }

    override fun onResume() {
        super.onResume()
        rotationVectorSensor?.also { sensor ->
            sensorManager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_UI)
        }
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
    }

    private fun connectWebSocket() {
        val url = getWsUrl()
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                runOnUiThread { statusTextView.text = "Status: Connected ($url)" }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val newCommandedAzimuth = when (text.trim().uppercase()) {
                    "UP" -> 0f    // North
                    "RIGHT" -> 90f // East
                    "DOWN" -> 180f // South
                    "LEFT" -> 270f // West
                    else -> null
                }

                if (newCommandedAzimuth != null) {
                    commandedAzimuth = newCommandedAzimuth
                    updateArrowRotation()
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                runOnUiThread { statusTextView.text = "Status: Closing" }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                runOnUiThread { statusTextView.text = "Status: Disconnected" }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                runOnUiThread {
                    statusTextView.text = "Status: Error - ${t.message ?: "unknown"}\nURL: $url"
                }
            }
        })
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event?.sensor?.type == Sensor.TYPE_ROTATION_VECTOR) {
            SensorManager.getRotationMatrixFromVector(rotationMatrix, event.values)
            SensorManager.getOrientation(rotationMatrix, orientationAngles)

            val azimuthRadians = orientationAngles[0]
            val azimuthDegrees = Math.toDegrees(azimuthRadians.toDouble()).toFloat()
            currentAzimuth = (azimuthDegrees + 360) % 360

            val direction = when {
                currentAzimuth >= 337.5 || currentAzimuth < 22.5 -> "N"
                currentAzimuth >= 22.5 && currentAzimuth < 67.5 -> "NE"
                currentAzimuth >= 67.5 && currentAzimuth < 112.5 -> "E"
                currentAzimuth >= 112.5 && currentAzimuth < 157.5 -> "SE"
                currentAzimuth >= 157.5 && currentAzimuth < 202.5 -> "S"
                currentAzimuth >= 202.5 && currentAzimuth < 247.5 -> "SW"
                currentAzimuth >= 247.5 && currentAzimuth < 292.5 -> "W"
                currentAzimuth >= 292.5 && currentAzimuth < 337.5 -> "NW"
                else -> "?"
            }

            runOnUiThread {
                directionTextView.text = direction
            }
            
            updateArrowRotation()
        }
    }

    private fun updateArrowRotation() {
        commandedAzimuth?.let { cmdAzimuth ->
            val rotation = cmdAzimuth - currentAzimuth
            runOnUiThread {
                arrowImageView.rotation = rotation
            }
        }
    }
}