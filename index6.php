<?php
session_start();
?>
<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);
?>
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Check if POST request was made
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
}
?>
<?php
echo "print_r post: ";
print_r($_POST);
echo "print_r SESSION: ";
print_r($_SESSION);
echo "<br/>";
?>
<?php
if (isset($_POST['video_delay'])) {
    $_SESSION['video_delay'] = $_POST['video_delay'];
    $_SESSION['video_dur'] = $_POST['video_dur'];
    $_SESSION['num_video'] = $_POST['num_video'];
}
?>
<?php
// "If isset" checks if the key "video_delay" exists in the $_POST superglobal array.
// In PHP, $_POST contains data sent to the server via an HTTP POST request.
// The isset() function checks if a specific variable or array key is set and not null.
if(isset($_COOKIE['video_delay'])) {
    echo "Your old cookie video_delay = " . $_COOKIE['video_delay'] . "<br>";
    echo "and video_dur = " . $_COOKIE['video_dur'] . "<br>";
    echo "and num_video = " . $_COOKIE['num_video'] . "<br>";
} else {
    echo "no cookie data";
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
if (file_exists($filename))
{echo "This page: $filename was modified: " . date ("Y-m-d H:i:s.", filemtime($filename));}
?>
<?php echo "  Time now: " .date("H:i:s") ?>
<!-- call the captureSelectedValue function when it's submitted -->
<!-- HTML form -->
<!--form method="post" action="/cgi-bin/select_data6.py" name="myform" onsubmit="captureSelectedValue()">
<form method="post" action="/cgi-bin/select_data6.py" name="myform">
    <!-- Your form fields and other elements -->
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
    </div>
    <p>

    <?php $dag = date("l") ?>
    Day for race <select name = "day" id="day">
    <option <?php if(isset($dag) && $dag == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
    <option <?php if(isset($dag) && $dag == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
    <option <?php if(isset($dag) && $dag == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
    <option <?php if(isset($dag) && $dag == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
    <option <?php if(isset($dag) && $dag == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
    <option <?php if(isset($dag) && $dag == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
    <option <?php if(isset($dag) && $dag == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
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
    <p></p>
    <div class="w3" align="center">
    <input type = "submit" value = "Submit"/>
</form>
<?php
// Set session variables
// If they are set, it will use their values. If they are not set, it will use the
// default values (30, 10, and 7, respectively) for the session variables.
$_SESSION['video_delay'] = isset($video_delay) ? $video_delay : 30;
$_SESSION['video_dur'] = isset($video_dur) ? $video_dur : 10;
$_SESSION['num_video'] = isset($num_video) ? $num_video : 7;
$_SESSION['start_time'] = $start_time;
?>
    <!-- Here is our page's main content -->
    <main>
    <br><p></p>
    <div class="w3" align="center">
        <h5> <a href="/index.php">  Resultat sida  </a></h5>
    </div>
    </main>
</body>
</html>
