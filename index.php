<?php
//session_id("regattastart");
//session_start();
//echo " 4: session-id= " . session_id() . " ";
//echo " 5: efter session id ";
//print_r($_SESSION);
//echo " 7: efter print_r";
//echo "<br/>";
?>
<?php
$cookie_name1 = "video_delay";
$cookie_name2 = "video_dur";
$cookie_name3 = "num_video";
?>
<!DOCTYPE html>
<html>
<?php
// Echo session variables that were set on previous page
if(!empty($_SESSION[$cookie_name1]))
{
echo "session variables set on previous page: ";
echo "video_delay = " . $_SESSION["video_delay"] . ", ";
echo "video_dur =  " . $_SESSION["video_dur"] . ", ";
echo "num_video = " . $_SESSION["num_video"] . ", ";
echo "<br/>";
$num_video = $_SESSION["num_video"];
} else {
echo " No Session data <br>";
}
?>
<?php
if(!isset($_COOKIE[$cookie_name2]))
{
   echo "no cookie data";
   if(empty($_SESSION[$cookie_name1]))
   {
       echo "no session data";
       $num_video = 7;
    } else {
       // Session  data exists
       echo "Video duration in minutes is set to = " . $_SESSION[$cookie_name1];
       echo " and ";
       echo "Video delay in minutes is: " . $_SESSION[$cookie_name2];
       echo "</br>";
       echo "Number of consecutive videos are: " . $_SESSION[$cookie_name3];
       $num_video = $_SESSION["num_video"];
     }
} else {
   echo " cookie data exists with: ";
   echo " video_delay=" . $_COOKIE["video_delay"];
   echo ", video_dur=" . $_COOKIE["video_dur"];
   echo ", cookie num_video=" . $_COOKIE["num_video"];
   echo "<br/>";
   $num_video = $_COOKIE["num_video"];
   echo "Number of finish videos vill be " . $num_video, " and each have a duration of ". $_COOKIE[$cookie_name2], " min";
}
?>
<body>
<head>
<title>Regattastart</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
img {
    max-width: 100%;
    height: auto;
}
</style>
<style>
video {
    max-width: 100%;
    height: auto;
}
</style>
<link rel="stylesheet" href="/w3.css"
</head>
<body>
<!-- Here is our main header that is used across all the pages of our website -->
<header>
<div align="center">
<div class="w3-panel w3-green">
<h2>Regattastart result page v7.0 </h2>
</div>
<?php
// output index.php was last modified.
$filename = 'index.php';
if (file_exists($filename))
{
   echo "This web-page was last modified: \n" . date ("Y-m-d H:i:s.", filemtime($filename));
}
?>
<?php echo "Time now: " .date("yH:i:s")?>
<br>
<!-- Here is our page's main content -->
<main>
<div align="center">
<h4><a href="/index6.php" title="Version using sessions"> Regattstart1 för 1 start</a></h4>
<div align="center">
<h4><a href="/index7.php" title="Version using sessions"> Regattstart2 för 2 starter</a></h4>
<div align="center">
<h3> Bilder tagna vid varje signal innan 1a start </h3>
<h3> Bild vid varningssignal 5 minuter innan 1a start</h3>
<img src="/images/1st-5min_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 5 min picture" width="720" height="480"  >
<h3> Bild vid signal 4 minuter innan 1a start</h3>
<img src="/images/1st-4min_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 4 min picture" width="720" height="480"  >
<h3> Bild vid signal 1 minut innan 1a start</h3>
<img src="/images/1st-1min_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st 1 min picture" width="720" height="480"  >
<h3> Foto vid 1a start</h3>
<img src="/images/1st-start_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="1st start  picture" width="720" height="480"  >
<?php
$filename = '/images/2nd-5min_pict.jpg';
if (file_exists($filename))
{
   echo "<h3> Bilder tagna vid varje signal innan 2a start </h3>";
   echo "<h3> Bild vid varningssignal 5 minuter innan 2a start</h3>";
   echo '<img src= "/images/2nd-5min_pict.jpg">';
//" "Date("Y.m.d.G.i.s")?>"; alt="2nd 5 min picture" width="720" height="480";
//echo "<h3> Signal 4 minuter innan 2a start</h3>";
//echo "<img src="/images/2nd-4min_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="2nd 4 min picture" width="720" height="480"  >";
//echo "<h3> Signal 1 minut innan 2a start</h3>";
//echo "<img src="/images/2nd-1min_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="2nd 1 min picture" width="720" height="480"  >";
//echo "<h3> Foto vid 2a start</h3>";
//echo "<img src="/images/2nd-start_pict.jpg?<?php echo Date("Y.m.d.G.i.s")?>" alt="2nd start  picture" width="720" height="480"  >"
//echo "<h2>Video for 5 minutes before 1st start and 5 minutes after 2nd start</h2>";
//echo "<video src="/images/video0.mp4?<?php echo Date("Y.m.d.G.i.s")?>" controls >HTML5 Video is required for this example</video>";
}
?>
<?php
for ($x = 1; $x <= $num_video; $x++) {
    echo "<h2> Finish video, this is video $x for the finish</h2><br>";
    $video_name =  "/images/video" . $x . ".mp4";
    echo "<video src=" . $video_name . " controls ></video><p>";
}
?>
</div>
</main>
</body>
</html>
