<?php
session_id("regattastart");
session_start();
echo "Session id = " . Session_id() . " ";
print_r($_SESSION);
echo "<br/>";
?>
<?php
if(isset($_POST['video_delay'])) {
// cookie
     $expires = (time()+3600*24*365);
     setcookie('video_delay',$_POST['video_delay'],$expires,'/');
     setcookie('video_dur',$_POST['video_dur'],$expires,'/');
     setcookie('num_video',$_POST['num_video'],$expires,'/');
}
?>
<?php
$cookie_name1 = "video_delay";
$cookie_name2 = "video_dur";
$cookie_name3 = "num_video";
?>
<?php
if(isset($_COOKIE[$cookie_name2])) {
//    echo " cookie " . $cookie_name1 . " is set!";
    $video_delay = $_COOKIE['video_delay'];
    $video_dur = $_COOKIE['video_dur'];
    $num_video = $_COOKIE['num_video'];
    echo " Your old cookie video_delay = ".$video_delay;
    echo ("\n");
    echo " and video_dur = ".$_COOKIE['video_dur'];
    echo ("\n");
    echo " and num_video = ".$_COOKIE['num_video'];
    echo ("\n");
    echo "<br/>";
    echo " Your new value for video_delay: ".$_POST['video_delay'];
    echo " and new video_dur: ".$_POST['video_dur'];
    echo " and new num_video: ".$_POST['num_video'];
    } else {
        echo "no cookie data  ";
}
?>
<?php
// Set session variables
$session_variable1 = "video_delay";
$session_variable2 = "video_dur";
$session_variable3 = "num_video";
// if sessions exists no action
if(isset($_SESSION[$session_variable1])){
//   echo "Session variables are set. ";
//   echo "Session variables video_delay= " . $_SESSION[$session_variable1] ."." ;
   // if sessions does not exist copy from cookies
   } else {
       echo "Session variables are not set. ";
       // if sessions does not exist but cookies exist
       if(isset($_COOKIE[$cookie_name2])) {
           echo "no session data but, cookies are set. ";
           $_SESSION["video_delay"] = $video_delay;
           $video_delay = $video_delay;
           $_SESSION["video_dur"] = $video_dur;
           $video_dur = $video_dur;
           $_SESSION["num_video"] = $num_video;
           $num_video = $num_video;
           // No session data and no cookie data, default will be set
           } else {
              echo "Session variables was not yet set, default will be set. ";
              $_SESSION["video_delay"] = 30;
              $video_delay = 30;
              $_SESSION["video_dur"] = 10;
              $video_dur = 10;
              $_SESSION["num_video"] = 7;
              $num_video = 7;
              echo "Session variables are given default values.  ";
           }
}
// print_r($_SESSION);
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
{echo "This page: $filename was modified: " . date ("Y-m-d H:i:s.", filemtime($filename));}?>
<?php echo "  Time now: " .date("H:i:s") ?>
<!-- Here is our main header that is used across all the pages of our website -->
<header>
<form method="post" action = "/cgi-bin/select_data6.py" name='myform'>
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
    $time = sprintf('%02d:%02d', $i/(60/$steps), $current%60);
    echo '<option>' . $time . '</option>';
    $current += $steps;
}
?>
</select>
</div>
<p>
<?php $idag = date("l") ?>
Day for race <select name = "day" id="day">
<option <?php if(isset($idag) && $idag == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
<option <?php if(isset($idag) && $idag == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
<option <?php if(isset($idag) && $idag == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
<option <?php if(isset($idag) && $idag == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
<option <?php if(isset($idag) && $idag == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
<option <?php if(isset($idag) && $idag == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
<option <?php if(isset($idag) && $idag == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
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
<option <?php if(isset($video_delay) && $video_dur == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
<option <?php if(isset($video_delay) && $video_dur == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
<option <?php if(isset($video_delay) && $video_dur == "15"){echo "selected=\"selected\"";} ?> value="15">15</option>
<option <?php if(isset($video_delay) && $video_dur == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
<option <?php if(isset($video_delay) && $video_dur == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
<option <?php if(isset($video_delay) && $video_dur == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
<option <?php if(isset($video_delay) && $video_dur == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
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
<p></p>
</div>
<?php
// Set session variables
$_SESSION["video_delay"] = $video_delay;
$_SESSION["video_dur"] = $video_dur;
$_SESSION["num_video"] = $num_video;
$_SESSION["start_time"] = $start_time;
echo "Session variables are set. ";
echo "video delay = " . $_SESSION["video_delay"] . ". ";
echo "video_dur = " . $_SESSION["video_dur"] . ". " ;
echo "num_video = " . $_SESSION["num_video"] . "." ;
echo "start_time = " . $_SESSION["start_time"] . "." ;
?>
<p></p>
<input type = "submit" value = "Submit"/>
</form>
<!-- Here is our page's main content -->
<main>
<h5> <a href="/index.php">  Resultat sida  </a></h5>
</main>
</div>
</body>
</html>
<?php
flush();
?>
