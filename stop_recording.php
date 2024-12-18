<?php
// Specify the correct path to the named pipe
$pipePath = '/var/www/html/tmp/stop_recording_pipe';
include_once 'functions.php';
// Open the named pipe for writing
$pipeHandle = fopen($pipePath, 'w');
if ($pipeHandle === false) {
    // Handle error
    $lastError = error_get_last();
    console_log('Stop_recording.php Failed to open named pipe: ' . $lastError['message']);
    die('Failed to open named pipe.');
} else {
    console_log('Stop_recording.php Line 22: Opened pipe handle successfully: ' . $pipeHandle);
}

$message = 'stop_recording';
if (fwrite($pipeHandle, $message) === false) {
    // Log error if writing to pipe fails
    console_log('Stop_recording.php Line 28: Failed to write message to named pipe.');
} else {
    // Log success message
    console_log('Stop_recording.php Line 31: Message sent to named pipe: ' . $message);
}

if (fclose($pipeHandle) === false) {
    console_log('Stop_recording.php Line 38: Failed to close pipe.');
} else {
    // Log success message
    console_log('Stop_recording.php Line 38: succesfully closed the pipe:');
}
?>