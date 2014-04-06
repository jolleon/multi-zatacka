var canvas = $('canvas').get(0);
var ctx = canvas.getContext("2d");

var loop_counter = 0;
var next_step = 0;

var startAnimation = function(){
    var requestAnimFrame = window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame    ||
            window.oRequestAnimationFrame      ||
            window.msRequestAnimationFrame     ||
            null ;

    next_step = Date.now();
    startTime = Date.now();
    lastStep = 1;
    lastGameStep = 1;
    if ( requestAnimFrame !== null ) {

        var recursiveAnim = function() {
            mainloop();
            requestAnimFrame( recursiveAnim, canvas );
        };

        // start the mainloop
        requestAnimFrame( recursiveAnim, canvas );
    } else {
        var ONE_FRAME_TIME = 1000.0 / 60.0 ;
        setInterval( mainloop, ONE_FRAME_TIME );
    }
};


var freq = 30;
var delay = 1000 / freq;
var avgBrowserDelay = 1.0 / 60;
var avgDelay = 1.0 / freq;

var fpss = [];
var gfpss = [];
var gameIterations = 0;
var smoothing = 0.5;

var mainloop = function(){
	loop_counter++;
    now = Date.now();
    avgBrowserDelay = smoothing * avgBrowserDelay + (1 - smoothing) * (now - lastStep);
    fpss.push(1000 / avgBrowserDelay);
    lastStep = now;

    if (2 * gameIterations % freq === 0){
        // 1 second
        bg = (gameIterations / 10) % 2 ? 'rgb(100,0,0)': 'rgb(0,0,100)';
    }
    now = Date.now();
    while (now > next_step){
        now = Date.now();
        avgDelay = smoothing * avgDelay + (1 - smoothing) * (now - lastGameStep);
        lastGameStep = now;
        // update game state
        drawGame();
        next_step += delay;
        gameIterations++;
    }
    gfpss.push(1000 / avgDelay);
}


var clearCanvas = function() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}


var drawGame = function() {
    clearCanvas();
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawFps();
    drawSnakes();
}

var drawFps = function() {
    ctx.fillStyle = 'yellow';
    ctx.font = "14px Lucida Console";
    ctx.fillText("Fps: " + Math.floor(10000 / avgBrowserDelay)/10, 0, 20);
    ctx.fillText("Game Fps: " + Math.floor(10000 / avgDelay)/10, 0, 40);
    ctx.fillText("delay: " + delay, 0, 60);
    ctx.fillText("it: " + loop_counter, 0, 80);
    ctx.fillText("Game time: " + (now - startTime) / 1000, 0, 100);

    ctx.strokeStyle = 'yellow';
    ctx.beginPath();
    ctx.moveTo(0, canvas.height)
    for (var i = 0; i < canvas.width; i++){
        if (canvas.width - i > fpss.length)
            continue;
        ctx.lineTo(i, canvas.height - fpss[fpss.length - canvas.width + i]);
    }
    ctx.stroke();
    ctx.moveTo(0, canvas.height)
    for (var i = 0; i < canvas.width; i++){
        if (canvas.width - i > gfpss.length)
            continue;
        ctx.lineTo(i, canvas.height - gfpss[gfpss.length - canvas.width + i]);
    }
    ctx.stroke();

}



$(document).ready(function() {

        // start the loop
        startAnimation();

        // listen to key press
        //window.addEventListener('keyup', function(event){Keys.onKeyup(event);}, false);
        //window.addEventListener('keydown', function(event){Keys.onKeydown(event);}, false);

});



var inbox = new ReconnectingWebSocket("ws://"+ location.host + "/receive");
var outbox = new ReconnectingWebSocket("ws://"+ location.host + "/submit");

snakes = [];

drawSnakes = function(){
    for(var i=0; i<snakes.length; i++){
        ctx.fillStyle = 'green';
        ctx.fillRect(snakes[i].x, snakes[i].y, 10, 10);

        ctx.fillText(snakes[i].name, 200, 20 + 20*i);
    }
}

inbox.onmessage = function(message) {
  console.log('received: ' + message)
  console.log('received data: ' + message.data)
  var data = JSON.parse(message.data);
  console.log('received data data: ' + data)
  snakes = data;
};

inbox.onclose = function(){
    console.log('inbox closed');
    this.inbox = new WebSocket(inbox.url);

};

outbox.onclose = function(){
    console.log('outbox closed');
    this.outbox = new WebSocket(outbox.url);
};
