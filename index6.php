<?php
session_start();
ini_set('display_errors', 1);
error_reporting(E_ALL);
echo "print_r post: ";
print_r($_POST);
echo "print_r SESSION: ";
print_r($_SESSION);
echo "<br/>";
?>

<?php
// Set the initial values for PHP variables (on each page load)
$num_video = null;

// Check if the form has been submitted
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Check if POST request was made and the form fields are set
    if (isset($_POST['num_video'])) {
        $num_video = $_POST['num_video'];
    }
}
// Check if the form has been submitted
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Check if POST request was made and the form fields are set
    if (isset($_POST['video_delay'])) {
        $_SESSION['video_delay'] = $_POST['video_delay'];
    }
    if (isset($_POST['video_dur'])) {
        $_SESSION['video_dur'] = $_POST['video_dur'];
    }
    if (isset($_POST['num_video'])) {
        $_SESSION['num_video'] = $_POST['num_video'];
    }
    if (isset($_POST['start_time'])) {
        $_SESSION['start_time'] = $_POST['start_time'];
    }
} else {
    error_log("Check if the form has been submitted");
    echo "<p> Check if the form has been submitted</p>";
}    
?>
<?php
// php code
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Check if POST request was made and the form fields are set
    if (isset($_POST['num_video'])) {
        $num_video = $_POST['num_video'];
        $_SESSION['sess_num_video'] = $num_video;
    }
    try {
        // Convert data to appropriate types
        $start_time = $_POST['start_time'];
        $week_day = $_POST['day'];
        $num_video = intval($_POST['num_video']);
        $video_delay = intval($_POST['video_delay']);
        $video_dur = intval($_POST['video_dur']);

        // Build the execution string for your Python script
        $execution_string = "python3 /usr/lib/cgi-bin/regattastart6.py $start_time $week_day $video_delay $num_video $video_dur &";
        //exec($execution_string);
        // Execute the Python script
        
        exec($execution_string, $output, $return_code);
        // $output will contain the output of the executed script
        // $return_code will contain the return code of the executed script

        // Check if the execution was successful
        if ($return_code === 0) {
            $response = ["message" => "Data processed successfully"];
        } else {
            $response = ["message" => "Error: Failed to process data"];
        }

        // Respond with a JSON message
        header("Content-Type: application/json");
        echo json_encode($response);
    } catch (Exception $e) {
        echo "<html><body>";
        echo "Error: Some fields contain invalid values.";
        echo "</body></html>";
    }
}
?>

<!DOCTYPE html>
<html>
<div align="center">
<head><title> Regattastart 1 för setup av en start </title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/w3.css"
</head>
<body>
<div class="w3-container w3-green">
<h2>Regattastart 1 för setup av en start</h2>
</div>
<!-- Here is our main header that is used across all the pages of our website -->
<meta http-equiv="refresh" content="200" >
<header>
</div>
<div align="center">
<?php
    // output index6.php was last modified.
    $filename = 'index6.php';
    if (file_exists($filename)) {
        echo "This page: $filename was modified: " . date ("Y-m-d H:i:s.", filemtime($filename));
    }
?>
<?php echo "  Time now: " .date("H:i:s") ?>
<!-- Use JavaScript to submit the form via AJAX -->
<script>
    function submitForm() {
        console.log("Form is being submitted");
        var formData = new FormData(document.getElementById("myform"));
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "index6.php", true);
        xhr.onload = function () {
            if (xhr.status === 200) {
                console.log("xhr.responseText");
                var response = JSON.parse(xhr.responseText);
                // Handle the response from the Python script (xhr.responseText)
                document.getElementById("result").innerHTML = xhr.responseText;
            } else {
                // Handle errors or failed request
                document.getElementById("result").innerHTML = "Error: " + xhr.status;
            } 
        };
        xhr.send(formData);
    }
</script>
<body>
<!-- HTML form -->
<div align="center">
    <form id="myform" onsubmit="event.preventDefault(); submitForm();">
        <!-- Your  fields here -->
        <div class="w3-row-padding" align="center">
        <div class="w3-half" align="center">
            <fieldset>
                <h4>Day and time setup</h4>
                <div data-tap-disabled="true">
                Start Time: <select name = "start_time" id = "start_time">
                <?php
                    $hour = date('H');
                    $steps   = 10; // only edit the minutes value
                    $current = 0;
                    $loops   = 24*(60/$steps);
                    //$loops   = (24-$hour)*(60/$steps);
                    //for ($i = $hour*(60/$steps); $i < $loops; $i++) {
                    for ($i = 0; $i < $loops; $i++) {
                    //    $time = sprintf('%02d:%02d', $i/(60/$steps), $current%60);
                    $start_time = sprintf('%02d:%02d', $i/(60/$steps), $current%60);
                    echo '<option>' . $start_time . '</option>';
                    $current += $steps;
                    }
                ?>
                </select>
                </div><p>
                <?php $day = date("l") 
                ?>
                Day for race <select name = "day" id="day">
                <option <?php if(isset($day) && $day == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
                <option <?php if(isset($day) && $day == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
                <option <?php if(isset($day) && $day == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
                <option <?php if(isset($day) && $day == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
                <option <?php if(isset($day) && $day == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
                <option <?php if(isset($day) && $day == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
                <option <?php if(isset($day) && $day == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
                </select>
            </fieldset>
        </div>
        <div class="w3-half" align="center">
            <fieldset>
                <h4>Video Setup</h4>
                <p></p>
                Duration between start and estimated finish: <select name = "video_delay" id = "video_delay">
                <option <?php if(isset($video_delay) && $video_delay == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
                <option <?php if(isset($video_delay) && $video_delay == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
                <option <?php if(isset($video_delay) && $video_delay == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
                <option <?php if(isset($video_delay) && $video_delay == "40"){echo "selected=\"selected\"";} ?> value="40">40</option>
                <option <?php if(isset($video_delay) && $video_delay == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
                <option <?php if(isset($video_delay) && $video_delay == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                <option <?php if(isset($video_delay) && $video_delay == "70"){echo "selected=\"selected\"";} ?> value="70">70</option>
                <option <?php if(isset($video_delay) && $video_delay == "80"){echo "selected=\"selected\"";} ?> value="80">80</option>
                </select>
                <p></p>
                Duration for each video: <select name = "video_dur" id = "video_dur">
                <option <?php if(isset($video_dur) && $video_dur == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                <option <?php if(isset($video_dur) && $video_dur == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
                <option <?php if(isset($video_dur) && $video_dur == "15"){echo "selected=\"selected\"";} ?> value="15">15</option>
                <option <?php if(isset($video_dur) && $video_dur == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
                <option <?php if(isset($video_dur) && $video_dur == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
                <option <?php if(isset($video_dur) && $video_dur == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
                <option <?php if(isset($video_dur) && $video_dur == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                </select>
                <p></p>
                Number of video's: <select name = "num_video" id = "num_video">
                <option <?php if(isset($num_video) && $num_video == "9"){echo "selected=\"selected\"";} ?> value="9">9</option>
                <option <?php if(isset($num_video) && $num_video == "8"){echo "selected=\"selected\"";} ?> value="8">8</option>
                <option <?php if(isset($num_video) && $num_video == "7"){echo "selected=\"selected\"";} ?> value="7">7</option>
                <option <?php if(isset($num_video) && $num_video == "6"){echo "selected=\"selected\"";} ?> value="6">6</option>
                <option <?php if(isset($num_video) && $num_video == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
                <option <?php if(isset($num_video) && $num_video == "4"){echo "selected=\"selected\"";} ?> value="4">4</option>
                <option <?php if(isset($num_video) && $num_video == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
                <option <?php if(isset($num_video) && $num_video == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                <option <?php if(isset($num_video) && $num_video == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                </select>
            </fieldset>
        </div>
        <br><p></p>
        <div id="submit" align="center"></div>
        <div class="w3" align="center">
        <br>
        <input type = "submit" value = "Submit"/input>
    </form>
</div>          
<!-- Here is our page's main content -->
<main>
    <br>
    <div id="result" align="center"></div>
    <div class="w3" align="center">
    <br>
    <h5> <a href="/index.php">  Resultat sida  </a></h5>
    </div>
</main>
</body>
</html>
