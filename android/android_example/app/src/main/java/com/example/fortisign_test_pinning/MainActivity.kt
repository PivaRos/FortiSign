package com.example.FortiSign

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.FortiSign.ui.theme.FortiSignTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            FortiSignTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    FetchGoogleContent(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }
}

@Composable
fun FetchGoogleContent(modifier: Modifier = Modifier) {
    var responseText by remember { mutableStateOf("Fetching...") }

    // Fetch data in a coroutine
    LaunchedEffect(Unit) {
        responseText = fetchGoogle()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(text = "chatgpt Response:", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(8.dp))
        Text(text = responseText, style = MaterialTheme.typography.bodyMedium)
    }
}

// OkHttp Request Function
suspend fun fetchGoogle(): String {
    return withContext(Dispatchers.IO) {
        val client = OkHttpClient()
        client.connectionPool.evictAll()
        val request = Request.Builder()
            .url("https://www.chatgpt.com")
            .build()

        client.newCall(request).execute().use { response ->
            if (response.isSuccessful) {
                response.body?.string() ?: "No response body"
            } else {
                "Error: ${response.code}"
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun FetchGoogleContentPreview() {
    FortiSignTheme {
        FetchGoogleContent()
    }
}
