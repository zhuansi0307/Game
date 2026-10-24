package com.partsvision.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Draw
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.DocumentScanner
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.partsvision.app.ui.AppViewModel
import com.partsvision.app.ui.LibraryScreen
import com.partsvision.app.ui.PartDetailScreen
import com.partsvision.app.ui.PartEditScreen
import com.partsvision.app.ui.RecognizeScreen
import com.partsvision.app.ui.SettingsScreen
import com.partsvision.app.ui.SketchScreen
import android.net.Uri

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab("recognize", "识别", Icons.Default.DocumentScanner),
    Tab("library", "零件库", Icons.Default.Inventory2),
    Tab("sketch", "草图出图", Icons.Default.Draw),
    Tab("settings", "设置", Icons.Default.Settings),
)

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val scheme = if (isSystemInDarkTheme()) darkColorScheme(primary = Color(0xFF90CAF9))
            else lightColorScheme(primary = Color(0xFF1565C0))
            MaterialTheme(colorScheme = scheme) { App(vm) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun App(vm: AppViewModel) {
    val nav = rememberNavController()
    val entry by nav.currentBackStackEntryAsState()
    val route = entry?.destination?.route
    val tab = tabs.firstOrNull { it.route == route }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(tab?.label ?: titleFor(route)) },
                navigationIcon = {
                    if (tab == null) IconButton(onClick = { nav.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回")
                    }
                },
            )
        },
        bottomBar = {
            if (tab != null) NavigationBar {
                tabs.forEach { t ->
                    NavigationBarItem(
                        selected = t.route == route,
                        onClick = { nav.switchTab(t.route) },
                        icon = { Icon(t.icon, null) },
                        label = { Text(t.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(nav, startDestination = "recognize", modifier = Modifier.padding(padding)) {
            composable("recognize") {
                RecognizeScreen(
                    vm,
                    onOpenPart = { nav.navigate("part/$it") },
                    onAddFromPhoto = { number -> nav.navigate("edit?number=${Uri.encode(number)}&fromRecognition=true") },
                )
            }
            composable("library") {
                LibraryScreen(vm, onOpenPart = { nav.navigate("part/$it") }, onAdd = { nav.navigate("edit") })
            }
            composable("sketch") { SketchScreen(vm) }
            composable("settings") { SettingsScreen(vm) }
            composable(
                "edit?number={number}&fromRecognition={fromRecognition}",
                arguments = listOf(
                    navArgument("number") { type = NavType.StringType; defaultValue = "" },
                    navArgument("fromRecognition") { type = NavType.BoolType; defaultValue = false },
                ),
            ) { e ->
                val fromRecognition = e.arguments?.getBoolean("fromRecognition") == true
                PartEditScreen(
                    vm,
                    initialNumber = e.arguments?.getString("number").orEmpty(),
                    initialPhoto = if (fromRecognition) vm.recognize.value.photo else null,
                    onDone = { id ->
                        nav.navigate("part/$id") { popUpTo("edit?number={number}&fromRecognition={fromRecognition}") { inclusive = true } }
                    },
                )
            }
            composable("part/{id}") { e ->
                PartDetailScreen(
                    vm, e.arguments?.getString("id").orEmpty(),
                    onAddPhotos = { number -> nav.navigate("edit?number=${Uri.encode(number)}") },
                    onDeleted = { nav.popBackStack() },
                )
            }
        }
    }
}

private fun titleFor(route: String?) = when {
    route == null -> ""
    route.startsWith("edit") -> "录入零件"
    route.startsWith("part") -> "零件详情"
    else -> ""
}

private fun NavHostController.switchTab(route: String) = navigate(route) {
    popUpTo(graph.findStartDestination().id) { saveState = true }
    launchSingleTop = true
    restoreState = true
}
