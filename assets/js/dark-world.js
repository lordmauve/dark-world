if ( ! Detector.webgl ) Detector.addGetWebGLMessage();

var container, stats, controls;
var camera, scene, renderer, light;

const tex_loader = new THREE.TextureLoader();
const model_loader = new THREE.GLTFLoader();


function load_skin(name) {
    var skin = tex_loader.load('textures/skins/skin_' + name + '.png');
    skin.flipY = false;
    return skin;
}


function load_model(name, skin, onload) {
    model_loader.load('models/' + name + '.gltf', function ( gltf ) {
        gltf.scene.traverse( function ( child ) {
            if ( child.isMesh ) {
                if (skin) {
                    const skin = load_skin('adventurer');
                    child.material.map = skin;
                }
                child.castShadow = true;
                child.receiveShadow = true;
            }
        } );

        let model = gltf.scene;
        scene.add(model);
        if (onload) {
            onload(model);
        }
    });
}

const TILE_SIZE = 16;
const SLAB = new THREE.MeshBasicMaterial({
    color: 0x111111,
    side: THREE.DoubleSide,
    opacity: 0.1,
    transparent: true
});

const terrain = tex_loader.load('textures/terrain.png');
terrain.flip_y = false;
const WORLD = new THREE.MeshPhongMaterial({
    shininess: 30,
    side: THREE.DoubleSide,
    map: terrain
});

var geometry = new THREE.PlaneGeometry(10240, 10240);
var ground = new THREE.Mesh(geometry, WORLD);
ground.receiveShadow = true;
ground.rotation.x = -Math.PI * 0.5;


function add_tile(material, x, z) {
    var geometry = new THREE.PlaneGeometry(15, 15);
    var plane = new THREE.Mesh(geometry, material);
    plane.receiveShadow = true;
    plane.rotation.x = -Math.PI * 0.5;
    plane.position.x = x * TILE_SIZE;
    plane.position.y = 0.1;
    plane.position.z = z * TILE_SIZE;
    scene.add( plane );
}


function init() {
    container = $('#viewport')[0];

    camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 1, 1000);
    camera.position.set(-30, 100, -100);
    camera.lookAt(0, 0, 0);

    /* Allow controlling view with the mouse
     */
    controls = new THREE.OrbitControls( camera );
    controls.target.set( 0, -2, -2 );
    controls.update();

    // envmap
    var path = 'textures/cube/skyboxsun25deg/';
    var format = '.jpg';
    var envMap = new THREE.CubeTextureLoader().load( [
        path + 'px' + format, path + 'nx' + format,
        path + 'py' + format, path + 'ny' + format,
        path + 'pz' + format, path + 'nz' + format
    ] );

    var head;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);
    scene.add(ground);

    light = new THREE.DirectionalLight(0xffffff);
    light.castShadow = true;
    light.position.set( -20, 6, -10 );
    light.shadow.mapSize.width = 1024;  // default
    light.shadow.mapSize.height = 1024; // default
    light.shadow.camera.near = 0.5;    // default
    light.shadow.camera.far = 100;     // default
    scene.add( light );

    light = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add( light );

    add_tile(SLAB, 0, 0);
    add_tile(SLAB, 1, 0);
    add_tile(SLAB, 1, 1);

    renderer = new THREE.WebGLRenderer( { antialias: true } );
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio( window.devicePixelRatio / 2);
    renderer.setSize( window.innerWidth, window.innerHeight);
    renderer.gammaOutput = true;
    container.appendChild( renderer.domElement );

    window.addEventListener( 'resize', onWindowResize, false );

    // stats
    stats = new Stats();
    container.appendChild( stats.dom );

    /* Animate the head
    var t = 0;
    setInterval(function () {
        t += 0.01;
        if (head) {
            head.rotation.y = 0.3 * Math.sin(t);
        }
    }, 10); */
}


function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight);
}


function animate() {
    requestAnimationFrame( animate );
    renderer.render( scene, camera );
    stats.update();
}


function log(msg, className) {
    var msg = $('<li>').text(msg).appendTo(messages);
    if (className) {
        msg.addClass(className);
    }
    setTimeout(
        $.proxy(msg.fadeOut, msg),
        5000,
        500,
        $.proxy(msg.remove, msg)
    );
}

function to_world(coord) {
    return [coord[0] * TILE_SIZE, coord[1] * TILE_SIZE];
}

function move_camera(x, z) {
    camera.position.set(x - 30, 100, z + 100);
    camera.lookAt(x, 0, z);
}

function refresh(msg) {
    let [x, z] = to_world(msg.pos);
    move_camera(x, z);
    for (let obj of msg.objs) {
        let [x, z] = to_world(obj.pos);
        load_model(obj.model, obj.skin, function(model) {
            model.name = obj.name;
            model.position.x = x;
            model.position.z = z;
            model.rotation.y = obj.dir * Math.PI / 2;
        });
    }
}

function on_moved(msg) {
    const obj = msg.obj;
    const existing = scene.getObjectByName(obj.name);
    const [x, z] = to_world(msg.to_pos);
    if (existing) {
        existing.position.x = x;
        existing.position.z = z;
        existing.rotation.y = obj.dir * Math.PI / 2;
    } else {
        load_model(obj.model, obj.skin, function(model) {
            model.name = obj.name;
            model.position.x = x;
            model.position.z = z;
            model.rotation.y = obj.dir * Math.PI / 2;
        });
    }
    if (msg.track) {
        move_camera(x, z);
    }
}

function on_killed(msg) {
    var existing = scene.getObjectByName(msg.name);
    if (existing) {
        scene.remove(existing);
    }
}

var ws;
var player_name = window.localStorage.player_name;

function send_msg(msg) {
    ws.send(JSON.stringify(msg));
}


while (!player_name) {
    player_name = prompt('What is your name?');
};


HANDLERS = {
    'announce': function (params) {
        log(params.msg);
    },
    'authfail': function (params) {
        log(params.msg, 'error');
        player_name = null;
        while (!player_name) {
            player_name = prompt('What is your name?');
        };
    },
    'authok': function (params) {
        window.localStorage.player_name = player_name;
    },
    'error': function (params) {
        log(params.msg, 'error');
    },
    'refresh': refresh,
    'moved': on_moved,
    'killed': on_killed
};


function connect() {
    ws = new WebSocket("ws://127.0.0.1:5988/");

    var messages = $('<ul id="messages">').appendTo(document.body);
    ws.onopen = function () {
        log('Connection established')
        send_msg({
            'op': 'auth',
            'name': player_name
        });
    };
    ws.onmessage = function (event) {
        let params = JSON.parse(event.data);
        let h = HANDLERS[params.op];
        if (!h) {
            throw "no handler for " + params.op;
        }
        h(params);
    };
    ws.onclose = function (event) {
        log('Connection closed: ' + event.code + ' ' + event.reason, 'error');
        setTimeout(connect, 2000);
    };
}


const KEYMAP = {
    38: 'north', // Up
    87: 'north', // W
    40: 'south', // Down
    83: 'south', // S
    37: 'west',  // Left
    65: 'west',  // W
    39: 'east',  // Right
    68: 'east',  // D
    32: 'act',  // Space
};


function initInput() {
   $(window).bind('keydown', function(event) {
        var keyCode = event.which;
        console.log(keyCode);
        op = KEYMAP[keyCode];
        if (op) {
            send_msg({'op': op});
        }
    });
}

init();
initInput();
connect();
animate();
