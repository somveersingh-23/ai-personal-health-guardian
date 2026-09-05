package com.healthguardian.app.presentation.ui.onboarding

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.components.PrimaryButton
import com.healthguardian.app.core.ui.theme.Spacing
import kotlinx.coroutines.launch
import androidx.compose.foundation.background

@Composable
fun OnboardingScreen(onComplete: () -> Unit) {
    val pagerState = rememberPagerState(pageCount = { 4 })
    val scope = rememberCoroutineScope()

    val pages = listOf(
        OnboardingPage("👋", "Welcome", "Your personal AI-powered health intelligence companion"),
        OnboardingPage("📊", "Your Health Profile", "We learn what's normal for you personally"),
        OnboardingPage("🧠", "Understand", "Learn your personal health baseline"),
        OnboardingPage("🛡️", "Guard", "Explain changes and provide safe guidance")
    )

    Box(modifier = Modifier.fillMaxSize().padding(Spacing.xl)) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                TextButton(onClick = onComplete) { Text("Skip") }
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier.weight(1f)
            ) { page ->
                OnboardingPageContent(pages[page])
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(vertical = Spacing.xl)
            ) {
                repeat(pages.size) { index ->
                    Box(
                        modifier = Modifier
                            .size(if (pagerState.currentPage == index) 12.dp else 8.dp)
                            .background(
                                color = if (pagerState.currentPage == index)
                                    MaterialTheme.colorScheme.primary
                                else
                                    MaterialTheme.colorScheme.surfaceVariant,
                                shape = CircleShape
                            )
                    )
                }
            }

            PrimaryButton(
                text = if (pagerState.currentPage == pages.lastIndex) "Get Started" else "Next",
                onClick = {
                    if (pagerState.currentPage == pages.lastIndex) {
                        onComplete()
                    } else {
                        scope.launch {
                            pagerState.animateScrollToPage(pagerState.currentPage + 1)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.xl)
            )

            Spacer(modifier = Modifier.height(Spacing.xxl))
        }
    }
}

@Composable
fun OnboardingPageContent(page: OnboardingPage) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxSize().padding(Spacing.xxl)
    ) {
        Text(text = page.icon, style = MaterialTheme.typography.displayLarge)
        Spacer(modifier = Modifier.height(Spacing.xxl))
        Text(
            text = page.title,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(Spacing.md))
        Text(
            text = page.description,
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

data class OnboardingPage(
    val icon: String,
    val title: String,
    val description: String
)