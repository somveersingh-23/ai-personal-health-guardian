package com.healthguardian.sensor.ui

import android.os.Bundle
import android.text.method.LinkMovementMethod
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.healthguardian.sensor.R

class PrivacyRationaleActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(ScrollView(this).apply {
            addView(TextView(context).apply {
                setText(R.string.privacy_rationale)
                textSize = 17f
                setPadding(40, 48, 40, 48)
                movementMethod = LinkMovementMethod.getInstance()
            })
        })
    }
}
