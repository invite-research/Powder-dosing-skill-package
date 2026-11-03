// --- Movement functions ---

void step_gripper_motor(int steps, int step_waittime) {
    for (int x = 0; x < steps; x++) {
        digitalWrite(stepPin_G, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_G, LOW);
        delayMicroseconds(step_waittime);
    }
}

int cm_to_gripper_steps(float distance_cm) {
    return (int)round(distance_cm * gripperStepsPerCm);
}

float clamp_float(float value, float min_value, float max_value) {
    if (value < min_value) return min_value;
    if (value > max_value) return max_value;
    return value;
}

void move_gripper_delta(float delta_cm, bool opening, int step_waittime = 0) {
    if (step_waittime == 0 || abs(step_waittime) < 100) {
        step_waittime = defaultGripperSpeed;
    }

    if (delta_cm <= 0.0) {
        Serial.println("Invalid gripper distance. No action taken.");
        if (client && client.connected()) client.print("Invalid gripper distance.");
        return;
    }

    float requested_target_cm;
    if (opening) {
        requested_target_cm = gripper_current_opening_cm + delta_cm;
    } else {
        requested_target_cm = gripper_current_opening_cm - delta_cm;
    }

    float clamped_target_cm = clamp_float(requested_target_cm, 0.0, gripperMaxOpeningCm);
    float actual_delta_cm = abs(clamped_target_cm - gripper_current_opening_cm);

    if (actual_delta_cm <= 0.0001) {
        if (opening) {
            Serial.println("Gripper already at maximum opening. No action taken.");
            if (client && client.connected()) client.print("Gripper already at maximum opening.");
        } else {
            Serial.println("Gripper already fully closed. No action taken.");
            if (client && client.connected()) client.print("Gripper already fully closed.");
        }
        return;
    }

    int steps_to_move = cm_to_gripper_steps(actual_delta_cm);
    if (steps_to_move <= 0) {
        Serial.println("Calculated gripper steps are zero. No action taken.");
        if (client && client.connected()) client.print("Calculated gripper steps are zero.");
        return;
    }

    Serial.print(opening ? "Opening gripper by cm: " : "Closing gripper by cm: ");
    Serial.println(actual_delta_cm, 3);

    // TMC2209: LOW = enabled, HIGH = disabled
    digitalWrite(enPin_G, LOW);
    digitalWrite(dirPin_G, opening ? gripperOpenDirLevel : gripperCloseDirLevel);

    step_gripper_motor(steps_to_move, step_waittime);

    gripper_current_opening_cm = clamped_target_cm;
    gripper_current_steps = cm_to_gripper_steps(gripper_current_opening_cm);
    gripper_target_steps = gripper_current_steps;

    Serial.print("Gripper opening now (cm): ");
    Serial.println(gripper_current_opening_cm, 3);

    if (client && client.connected()) {
        client.print("Gripper opening now (cm): ");
        client.print(gripper_current_opening_cm, 3);
    }
}

void open_gripper_by_cm(float delta_cm, int step_waittime = 0) {
    move_gripper_delta(delta_cm, true, step_waittime);
}

void close_gripper_by_cm(float delta_cm, int step_waittime = 0) {
    move_gripper_delta(delta_cm, false, step_waittime);
}

void tilt_station(int step_waittime = 8000) {
    // Set waittime, default is 8000.
    if (step_waittime == 0) {
        step_waittime = 8000;
    }

    Serial.println("Tilting...");
    int diff_positions = new_position_tilt - current_position_tilt;
    unsigned int steps = (abs(diff_positions) + offsetTilt) / degreePerStep;

    // Set direction depending on sign of diff_positions.
    // ** To tilt, motors move in opposite directions.
    if (diff_positions <= 0) {
        // Move CCW.
        digitalWrite(dirPin_L, LOW);
        digitalWrite(dirPin_R, HIGH);
    }
    else {
        // Move CW.
        digitalWrite(dirPin_L, HIGH);
        digitalWrite(dirPin_R, LOW);
    }

    // Enable both motors.
    digitalWrite(enPin_L, HIGH);
    digitalWrite(enPin_R, HIGH);

    // Actually move the motors.
    for (int x = 0; x <= steps; x++) {
        digitalWrite(stepPin_L, HIGH);
        digitalWrite(stepPin_R, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_L, LOW);
        digitalWrite(stepPin_R, LOW);
        delayMicroseconds(step_waittime);
    }

    // Update the new position.
    current_position_tilt = new_position_tilt;
    Serial.println("Finished.");
    if (client && client.connected()) client.print("Finished.");
}

void rotate_CW(int step_waittime = 8000) {
    Serial.println("Rotating (CW) ...");
    if (abs(step_waittime) < 1000) {
        step_waittime = 8000;
    }

    int diff_positions = new_position_rotation - current_position_rotation;
    if (diff_positions > 0) {
        diff_positions = 360 - diff_positions;
    }
    unsigned int steps = (abs(diff_positions) + offsetRotation) / degreePerStep;

    digitalWrite(dirPin_L, HIGH);
    digitalWrite(dirPin_R, HIGH);

    digitalWrite(enPin_L, HIGH);
    digitalWrite(enPin_R, HIGH);

    for (int x = 0; x <= steps; x++) {
        digitalWrite(stepPin_L, HIGH);
        digitalWrite(stepPin_R, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_L, LOW);
        digitalWrite(stepPin_R, LOW);
        delayMicroseconds(step_waittime);
    }

    current_position_rotation = new_position_rotation;
    Serial.println("Finished.");
    if (client && client.connected()) client.print("Finished.");
}

void rotate_CCW(int step_waittime = 8000) {
    Serial.println("Rotating (CCW) ...");
    if (abs(step_waittime) < 1000) {
        step_waittime = 8000;
    }

    int diff_positions = new_position_rotation - current_position_rotation;
    if (diff_positions < 0) {
        diff_positions = 360 - diff_positions;
    }
    unsigned int steps = (abs(diff_positions) + offsetRotation) / degreePerStep;

    digitalWrite(dirPin_L, LOW);
    digitalWrite(dirPin_R, LOW);

    digitalWrite(enPin_L, HIGH);
    digitalWrite(enPin_R, HIGH);

    for (int x = 0; x <= steps; x++) {
        digitalWrite(stepPin_L, HIGH);
        digitalWrite(stepPin_R, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_L, LOW);
        digitalWrite(stepPin_R, LOW);
        delayMicroseconds(step_waittime);
    }

    current_position_rotation = new_position_rotation;
    Serial.println("Finished.");
    if (client && client.connected()) client.print("Finished.");
}

void multiple_rotations(int revs = 1, int step_waittime = 8000) {
    if (step_waittime == 0) {
        step_waittime = 8000;
    }

    Serial.println("Rotating (multiple)...");

    if (revs >= 0) {
        digitalWrite(dirPin_L, HIGH);
        digitalWrite(dirPin_R, HIGH);
    }
    else {
        digitalWrite(dirPin_L, LOW);
        digitalWrite(dirPin_R, LOW);
    }

    digitalWrite(enPin_L, HIGH);
    digitalWrite(enPin_R, HIGH);

    for (int x = 0; x <= ((stepsPerRevolution + (offsetRotation / degreePerStep)) * abs(revs)); x++) {
        digitalWrite(stepPin_L, HIGH);
        digitalWrite(stepPin_R, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_L, LOW);
        digitalWrite(stepPin_R, LOW);
        delayMicroseconds(step_waittime);
    }

    Serial.println("Finished.");
    if (client && client.connected()) client.print("Finished.");
}

void rotate_for_time(int seconds = 10, int step_waittime = 8000) {
    if (step_waittime == 0) {
        step_waittime = 8000;
    }

    Serial.println("Rotating for time...");

    if (seconds >= 0) {
        digitalWrite(dirPin_L, HIGH);
        digitalWrite(dirPin_R, HIGH);
    }
    else {
        digitalWrite(dirPin_L, LOW);
        digitalWrite(dirPin_R, LOW);
    }

    digitalWrite(enPin_L, HIGH);
    digitalWrite(enPin_R, HIGH);

    int current_millis = millis();
    int steps = 0;

    while (millis() - current_millis <= abs(seconds) * 1000) {
        digitalWrite(stepPin_L, HIGH);
        digitalWrite(stepPin_R, HIGH);
        delayMicroseconds(step_waittime);
        digitalWrite(stepPin_L, LOW);
        digitalWrite(stepPin_R, LOW);
        delayMicroseconds(step_waittime);
        steps++;
    }

    if (seconds < 0) {
        steps = steps * -1;
    }

    current_position_rotation = current_position_rotation + (steps * degreePerStep);
    current_position_rotation = abs(current_position_rotation % 360);
    if (current_position_rotation < 0) {
        current_position_rotation = 360 - current_position_rotation;
    }
    new_position_rotation = current_position_rotation;

    Serial.print("Current position: ");
    Serial.println(current_position_rotation);

    Serial.println("Finished.");
    if (client && client.connected()) client.print("Finished.");
}

///////////////////////////////////////////////////////////////////////////////////////////////

// --- Communication functions ---

void interpret_message() {
    String movement = "";
    float msg_position = 0.0;
    int msg_speed = 0;

    int commaIndex = message.indexOf(',');
    int commaIndex_2 = message.indexOf(',', commaIndex + 1);

    if (commaIndex != -1 && commaIndex_2 != -1) {
        movement = message.substring(0, commaIndex);
        msg_position = (message.substring(commaIndex + 1, commaIndex_2)).toFloat();
        msg_speed = (message.substring(commaIndex_2 + 1)).toInt();
    } else {
        Serial.println("Message format invalid.");
        return;
    }

    mov_speed = msg_speed;
    gripper_action = "";

    if ((movement == "RotateCW") && (msg_position >= 0.0) && (msg_position < 360.0)) {
        new_position_rotation = (int)msg_position;
        direction_rotation = "CW";
    }
    else if ((movement == "RotateCCW") && (msg_position >= 0.0) && (msg_position < 360.0)) {
        new_position_rotation = (int)msg_position;
        direction_rotation = "CCW";
    }
    else if ((movement == "Tilt") && (msg_position >= 0.0) && (msg_position < 180.0)) {
        new_position_tilt = (int)msg_position;
        direction_rotation = "";
    }
    else if (movement == "FullRotation") {
        new_position_rotation = current_position_rotation;
        multiple_rotations((int)msg_position, mov_speed);
    }
    else if (movement == "RotateTime") {
        rotate_for_time((int)msg_position, mov_speed);
    }
    else if ((movement == "GripperOpen" || movement == "GripOpen") && (msg_position > 0.0)) {
        gripper_requested_delta_cm = msg_position;
        gripper_action = "OPEN";
        direction_rotation = "";
        new_position_tilt = current_position_tilt;
        new_position_rotation = current_position_rotation;
    }
    else if ((movement == "GripperClose" || movement == "GripClose") && (msg_position > 0.0)) {
        gripper_requested_delta_cm = msg_position;
        gripper_action = "CLOSE";
        direction_rotation = "";
        new_position_tilt = current_position_tilt;
        new_position_rotation = current_position_rotation;
    }
    else if (movement == "Home") {
        new_position_rotation = 0;
        new_position_tilt = 90;
        direction_rotation = "";
        gripper_action = "";

        if (current_position_rotation < 180) {
            direction_rotation = "CW";
        }
        else {
            direction_rotation = "CCW";
            current_position_rotation = current_position_rotation - 360;
        }
    }
    else if (movement == "Off") {
        digitalWrite(enPin_L, LOW);
        digitalWrite(enPin_R, LOW);
        digitalWrite(enPin_G, HIGH);   // TMC2209 disable
        
        gripper_action = "";
        Serial.println("Motors deactivated.");
    }
    else {
        new_position_tilt = current_position_tilt;
        new_position_rotation = current_position_rotation;
        direction_rotation = "";
        gripper_action = "";
    }
}