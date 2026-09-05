package com.healthguardian.app.presentation.ui.auth

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.common.Result
import com.healthguardian.app.core.ui.components.PrimaryButton
import com.healthguardian.app.core.ui.theme.Spacing
import com.healthguardian.app.presentation.viewmodel.AuthViewModel

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onNavigateToRegister: () -> Unit,
    viewModel: AuthViewModel = androidx.hilt.navigation.compose.hiltViewModel()
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.xl)
            .imePadding(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "🩺", style = MaterialTheme.typography.displayMedium)
        Spacer(modifier = Modifier.height(Spacing.xxl))

        Text(
            text = "Welcome Back",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Sign in to continue",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(Spacing.xl))

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            placeholder = { Text("your@email.com") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth(),
            isError = errorMessage != null
        )

        Spacer(modifier = Modifier.height(Spacing.md))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            placeholder = { Text("••••••••") },
            visualTransformation = PasswordVisualTransformation(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
            isError = errorMessage != null
        )

        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(Spacing.sm))
            Text(
                text = errorMessage!!,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
                textAlign = TextAlign.Center
            )
        }

        Spacer(modifier = Modifier.height(Spacing.lg))

        PrimaryButton(
            text = "Sign In",
            onClick = {
                isLoading = true
                errorMessage = null
                viewModel.login(email, password) { result ->
                    isLoading = false
                    when (result) {
                        is Result.Success -> onLoginSuccess()
                        is Result.Error -> errorMessage = result.message ?: "Login failed"
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            isLoading = isLoading,
            enabled = email.isNotBlank() && password.isNotBlank() && !isLoading
        )

        Spacer(modifier = Modifier.height(Spacing.lg))

        Row(
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Don't have an account?",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            TextButton(onClick = onNavigateToRegister) { Text("Sign Up") }
        }
    }
}