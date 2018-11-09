function updateClock() {
    var clock = document.getElementById("clock");
    var time_vals = clock.innerHTML.split(':');
    if(time_vals.length == 2){ time_vals.unshift('0');}
    var total_seconds = time_vals[0]*3600+time_vals[1]*60+time_vals[2]*1;
    function tick() {
        total_seconds--;

        var time = total_seconds;
        var hours = Math.floor(time / 3600);
        time = time - hours * 3600;
        var minutes = Math.floor(time / 60);
        var seconds = time - minutes * 60;
        var hours_str = (hours > 0 ? String(hours)+":":"")

        clock.innerHTML = hours_str + String(minutes) + ":" + (seconds < 10 ? "0" + String(seconds):String(seconds));
    }
    tick();
    if(total_seconds==0){
        clearInterval(timeinterval);
        setTimeout(function(){window.location.href = '/not-available/';}, 1000);
    }
}
var timeinterval = setInterval(updateClock,1000);

