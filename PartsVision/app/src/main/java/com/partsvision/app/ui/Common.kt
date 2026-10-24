package com.partsvision.app.ui

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.partsvision.app.util.ImageUtils
import kotlinx.coroutines.launch

class ImagePicker(val takePhoto: () -> Unit, val pickFromGallery: () -> Unit)

/** Camera + gallery launchers that deliver a decoded, upright, downscaled bitmap. */
@Composable
fun rememberImagePicker(vm: AppViewModel, multiple: Boolean = false, onImage: (Bitmap) -> Unit): ImagePicker {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var pendingUri by rememberSaveable { mutableStateOf<Uri?>(null) }

    fun deliver(uri: Uri) = scope.launch { vm.decode(uri)?.let(onImage) }

    val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val uri = pendingUri
        if (ok && uri != null) deliver(uri)
    }
    val single = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let(::deliver)
    }
    val many = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(10)) { uris ->
        uris.forEach(::deliver)
    }
    fun launchCamera() {
        val uri = ImageUtils.newCameraUri(context)
        pendingUri = uri
        camera.launch(uri)
    }
    // The app declares CAMERA (for the live scanner), so the system camera intent needs it granted too.
    val permission = rememberCameraPermission { granted -> if (granted) launchCamera() }
    return remember(multiple, permission.granted) {
        ImagePicker(
            takePhoto = { if (permission.granted) launchCamera() else permission.request() },
            pickFromGallery = {
                val request = PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                if (multiple) many.launch(request) else single.launch(request)
            },
        )
    }
}

@Composable
fun PickerButtons(picker: ImagePicker, modifier: Modifier = Modifier, cameraLabel: String = "拍照") {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(onClick = picker.takePhoto, modifier = Modifier.weight(1f)) {
            Icon(Icons.Default.PhotoCamera, null, Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(cameraLabel)
        }
        OutlinedButton(onClick = picker.pickFromGallery, modifier = Modifier.weight(1f)) {
            Icon(Icons.Default.PhotoLibrary, null, Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("相册")
        }
    }
}
