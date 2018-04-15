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


const SLAB = new THREE.MeshBasicMaterial({color: 0x111111, side: THREE.DoubleSide} );


function add_tile(material, x, z) {
    var geometry = new THREE.PlaneGeometry(16, 16);
    var plane = new THREE.Mesh(geometry, material);
    plane.receiveShadow = true;
    plane.rotation.x = Math.PI * 0.5;
    plane.position.x = x * 18;
    plane.position.z = z * 18;
    scene.add( plane );
}


function init() {
    container = document.createElement( 'div' );
    document.body.appendChild( container );

    camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 1, 1000);
    camera.position.set(-100, 100, -100);

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

    var skin = load_skin('adventurer');
    var head;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);

    light = new THREE.DirectionalLight(0xffffff);
    light.castShadow = true;
    light.position.set( -10, 6, -10 );
    light.shadow.mapSize.width = 512;  // default
    light.shadow.mapSize.height = 512; // default
    light.shadow.camera.near = 0.5;    // default
    light.shadow.camera.far = 500;     // default
    scene.add( light );

    light = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add( light );

    add_tile(SLAB, 0, 0);
    add_tile(SLAB, 1, 0);
    add_tile(SLAB, 1, 1);

    renderer = new THREE.WebGLRenderer( { antialias: true } );
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio( window.devicePixelRatio );
    renderer.setSize( window.innerWidth, window.innerHeight );
    renderer.gammaOutput = true;
    container.appendChild( renderer.domElement );

    window.addEventListener( 'resize', onWindowResize, false );

    load_model('advancedCharacter', skin, function (model) {
        head = model.getObjectByName('Head1');
    });

    // stats
    stats = new Stats();
    container.appendChild( stats.dom );

    var t = 0;
    setInterval(function () {
        t += 0.01;
        if (head) {
            head.rotation.y = 0.3 * Math.sin(t);
        }
    }, 10);
}


function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight );
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


var player_name = null;


function connect() {
    var ws = new WebSocket("ws://127.0.0.1:5988/");

    function send_msg(msg) {
        ws.send(JSON.stringify(msg));
    }

    while (!player_name) {
        player_name = prompt('What is your name?');
    };
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
        if (params.op == 'announce') {
            log(params.msg);
        }
    };
    ws.onclose = function (event) {
        log('Connection closed: ' + event.code + ' ' + event.reason, 'error');
        setTimeout(connect, 5000);
    };
}

init();
connect();
animate();
