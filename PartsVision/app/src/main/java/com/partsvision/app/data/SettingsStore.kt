package com.partsvision.app.data

import android.content.Context

/** App settings kept in app-private SharedPreferences. */
class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var apiKey: String
        get() = prefs.getString(KEY_API_KEY, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_API_KEY, value.trim()).apply()

    var model: String
        get() = prefs.getString(KEY_MODEL, DEFAULT_MODEL).orEmpty().ifBlank { DEFAULT_MODEL }
        set(value) = prefs.edit().putString(KEY_MODEL, value.trim()).apply()

    /** Ask the cloud model to confirm on-device matches when an API key is configured. */
    var cloudAssist: Boolean
        get() = prefs.getBoolean(KEY_CLOUD_ASSIST, true)
        set(value) = prefs.edit().putBoolean(KEY_CLOUD_ASSIST, value).apply()

    val hasApiKey: Boolean get() = apiKey.isNotBlank()

    companion object {
        const val DEFAULT_MODEL = "claude-opus-5-5"
        private const val KEY_API_KEY = "api_key"
        private const val KEY_MODEL = "model"
        private const val KEY_CLOUD_ASSIST = "cloud_assist"
    }
}
