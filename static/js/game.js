$(document).ready(function() {

var hudCanvas = $('#hud').get(0);
var hudctx = hudCanvas.getContext("2d");

var gCanvas = $('#game').get(0);
var gctx = gCanvas.getContext("2d");

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
            requestAnimFrame( recursiveAnim, hudCanvas );
        };

        // start the mainloop
        requestAnimFrame( recursiveAnim, hudCanvas );
    } else {
        var ONE_FRAME_TIME = 1000.0 / 60.0 ;
        setInterval( mainloop, ONE_FRAME_TIME );
    }
};


var freq = 60;
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


var clearHudCanvas = function() {
    hudctx.clearRect(0, 0, hudCanvas.width, hudCanvas.height);
}


var drawGame = function() {
    clearHudCanvas();
    hudctx.fillStyle = bg;
    hudctx.fillRect(0, 0, hudCanvas.width, hudCanvas.height);
    drawFps();
    drawSnakes();
}

var drawFps = function() {
    hudctx.fillStyle = 'yellow';
    hudctx.font = "14px Lucida Console";
    hudctx.fillText("Fps: " + Math.floor(10000 / avgBrowserDelay)/10, 0, 20);
    hudctx.fillText("Game Fps: " + Math.floor(10000 / avgDelay)/10, 0, 40);
    hudctx.fillText("delay: " + delay, 0, 60);
    hudctx.fillText("it: " + loop_counter, 0, 80);
    hudctx.fillText("Game time: " + (now - startTime) / 1000, 0, 100);

    hudctx.strokeStyle = 'yellow';
    hudctx.beginPath();
    hudctx.moveTo(0, hudCanvas.height)
    for (var i = 0; i < hudCanvas.width; i++){
        if (hudCanvas.width - i > fpss.length)
            continue;
        hudctx.lineTo(i, hudCanvas.height - fpss[fpss.length - hudCanvas.width + i]);
    }
    hudctx.stroke();
    hudctx.moveTo(0, hudCanvas.height)
    for (var i = 0; i < hudCanvas.width; i++){
        if (hudCanvas.width - i > gfpss.length)
            continue;
        hudctx.lineTo(i, hudCanvas.height - gfpss[gfpss.length - hudCanvas.width + i]);
    }
    hudctx.stroke();

}




// start the loop
startAnimation();

// listen to key press
window.addEventListener('keyup', function(event){Keys.onKeyup(event);}, false);
window.addEventListener('keydown', function(event){Keys.onKeydown(event);}, false);

var inbox = new ReconnectingWebSocket("ws://"+ location.host + "/receive");
var outbox = new ReconnectingWebSocket("ws://"+ location.host + "/submit");

inbox.onmessage = function(message) {
    //console.log('received data: ' + message.data)
    var data = JSON.parse(message.data);
    if (data.type === 'step') {
        snakesQueue.push(data.content);
    }
    if (data.type === 'restart') {
        gctx.clearRect(0, 0, gCanvas.width, gCanvas.height);
    }
    if (data.type === 'size') {
        gCanvas.width = data.width;
        gCanvas.height = data.height;
    }
    if (data.type === 'players') {
        $('#players').html('');
        for (var i=0; i<data.content.length; i++){
            player = data.content[i];
            $('#players').append('<div style="color:' + player.color + '">' +
                    player.id + ' - ' + player.name +
                    ': ' + player.score + '</div>')
        }
    }
};

inbox.onclose = function(){
    console.log('inbox closed');
    this.inbox = new WebSocket(inbox.url);

};

outbox.onclose = function(){
    console.log('outbox closed');
    this.outbox = new WebSocket(outbox.url);
};





snakesQueue = [];

drawSnakes = function(){
    for(var j=0; j<snakesQueue.length; j++){
        snakes = snakesQueue[j];
        for(var i=0; i<snakes.length; i++){
            gctx.fillStyle = snakes[i].color;
            gctx.fillRect(snakes[i].x, snakes[i].y, 5, 5);
        }
    }
    snakesQueue = [];
}

var Keys = {
    UP: [87, 38], // w
    DOWN: [83, 40], // s
    LEFT: [65, 37], // a
    RIGHT: [68, 39], // d

    _pressed: {},

    isDown: function(keyCode) {
        return this._pressed[keyCode[0]] || this._pressed[keyCode[1]];
    },

    onKeydown: function(event) {
        if(this._pressed[event.keyCode]) return;
        if(event.keyCode === this.LEFT[1]){
            outbox.send(JSON.stringify({ command: "left"}));
        }
        if(event.keyCode === this.RIGHT[1]){
            outbox.send(JSON.stringify({ command: "right"}));
        }

        this._pressed[event.keyCode] = true;
    },

    onKeyup: function(event) {
        if(event.keyCode === this.LEFT[1] && !this.isDown(this.RIGHT)){
            outbox.send(JSON.stringify({ command: "straight"}));
        }
        if(event.keyCode === this.RIGHT[1] && !this.isDown(this.LEFT)){
            outbox.send(JSON.stringify({ command: "straight"}));
        }
        delete this._pressed[event.keyCode];
    }
};

});
