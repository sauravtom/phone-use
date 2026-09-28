package org.phoneuse.fixture;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Isolated device fixture. No permissions, network access, or user data. */
public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 80, 32, 32);
        TextView title = new TextView(this);
        title.setText("phone-use device test");
        title.setTextSize(24);
        layout.addView(title);
        EditText input = new EditText(this);
        input.setContentDescription("Test input");
        input.setSingleLine(true);
        layout.addView(input);
        Button button = new Button(this);
        button.setText("Apply text");
        layout.addView(button);
        TextView result = new TextView(this);
        result.setText("Waiting for input");
        result.setTextSize(20);
        layout.addView(result);
        button.setOnClickListener(new android.view.View.OnClickListener() {
            @Override public void onClick(android.view.View view) {
                result.setText("Verified: " + input.getText());
            }
        });
        setContentView(layout);
    }
}
