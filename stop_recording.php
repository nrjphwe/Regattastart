<?php
echo "stop_recording.php executed.";
error_log('stop_recording.php: Script started.');
// Specify the correct path to the named pipe
$pipePath = '/var/www/html/tmp/stop_recording_pipe';
include_once 'functions.php';

// Check if the pipe exists
if (!file_exists($pipePath)) {
    error_log('Stop_recording.php: Pipe does not exist.');
    die('Pipe does not exist.');
}

// Check if the pipe is writable
if (!is_writable($pipePath)) {
    error_log('Stop_recording.php: Pipe is not writable.');
    die('Pipe is not writable.');
}

// Open the named pipe for writing
$pipeHandle = fopen($pipePath, 'w');
if ($pipeHandle === false) {
    // Handle error
    $lastError = error_get_last();
    error_log('Stop_recording.php Failed to open named pipe: ' . $lastError['message']);
    die('Failed to open named pipe.');
} else {
    error_log('Stop_recording.php Opened pipe handle successfully: ' . $pipeHandle);
}

$message = "stop_recording\n";
if (fwrite($pipeHandle, $message) === false) {
    // Log error if writing to pipe fails
    error_log('Stop_recording.php Failed to write message to named pipe.');
} else {
    // Log success message
    error_log('Stop_recording.php Message sent to named pipe: ' . $message);
}

if (fclose($pipeHandle) === false) {
    error_log('Stop_recording.php Failed to close pipe.');
} else {
    // Log success message
    error_log('Stop_recording.php succesfully closed the pipe:');
}
?>