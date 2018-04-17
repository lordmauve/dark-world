if ( ! Detector.webgl ) Detector.addGetWebGLMessage();

var container, stats, controls;
var camera, scene, renderer, light, sun, ambient, anims;

const tex_loader = new THREE.TextureLoader();
const model_loader = new THREE.GLTFLoader();

const INTERP = {
    linear: function(x) {
        return x;
    },

    hop: function(x) {
        return -4 * x * (x - 1);
    }
};


function animateProps(obj, attrs, opts) {
    var opts = opts || {};
    var start = 0;
    var duration = opts.duration || 100;
    var interp = opts.interp || INTERP.linear;
    var initial = {};
    for (k in attrs) {
        initial[k] = obj[k];
    }
    function step(timestamp) {
        if (!start) start = timestamp;
        var t = Math.max(
            Math.min((timestamp - start) / duration, 1),
            0
        );
        var frac = interp(t);
        var invfrac = 1.0 - frac;

        for (k in attrs) {
            obj[k] = invfrac * initial[k] + frac * attrs[k];
        }

        if (opts.each_frame) {
            opts.each_frame();
        }
        if (t < 1) {
            window.requestAnimationFrame(step);
        } else {
            if (opts.on_finish) {
                opts.on_finish();
            }
        }
    }
    window.requestAnimationFrame(step);
}


function load_skin(name) {
    var skin = tex_loader.load('textures/skins/skin_' + name + '.png');
    skin.flipY = false;
    return skin;
}


function load_model(obj, onload) {
    let model_name = obj.model;
    let skin_name = obj.skin || null;

    let scale = obj.scale || 1.0;

    model_loader.load('models/' + model_name + '.gltf', function ( gltf ) {
        let model = gltf.scene;
        if (model.children.length == 1) {
            model = model.children[0];
        }
        model.animations = gltf.animations;
        model.traverse( function ( child ) {
            if ( child.isMesh ) {
                if (skin_name) {
                    const skin = load_skin(skin_name);
                    child.material.map = skin;
                }
                child.castShadow = true;
                child.receiveShadow = true;
            }
        } );

        model.worldObj = true;
        model.name = obj.name;
        model.rotation.y = obj.dir * Math.PI / 2;
        if (scale != 1.0) {
            model.scale.set(scale, scale, scale);
        }

        scene.add(model);
        if (onload) {
            onload(model);
        }
    });
}

const SHADOW_SIZE = 100;
const TILE_SIZE = 16;
const SLAB = new THREE.MeshBasicMaterial({
    color: 0x111111,
    side: THREE.DoubleSide,
    opacity: 0.1,
    transparent: true
});

const TELEPORT = new THREE.MeshBasicMaterial({
    color: 0x1188DD,
    side: THREE.FrontSize,
    opacity: 0.5,
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
    if (scene) return;
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

    anims = new THREE.AnimationMixer(scene);
    anims.addEventListener('finished', function (e) {
        if (e.action.hide_on_finish) {
            e.action.getRoot().visible = false;
        }
    });

    sun = new THREE.DirectionalLight(0xffffff);
    sun.castShadow = true;
    sun.position.set( -200, 200, -100 );
    sun.shadow.mapSize.width = 1024;  // default
    sun.shadow.mapSize.height = 1024; // default
    sun.shadow.camera.left = -SHADOW_SIZE;
    sun.shadow.camera.right = SHADOW_SIZE;
    sun.shadow.camera.bottom = -SHADOW_SIZE;
    sun.shadow.camera.top = SHADOW_SIZE;
    sun.shadow.camera.near = 0.5;    // default
    sun.shadow.camera.far = 1000;     // default
    scene.add( sun );
    scene.add(sun.target);

    ambient = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add(ambient);

    /*
    add_tile(SLAB, 0, 0);
    add_tile(SLAB, 1, 0);
    add_tile(SLAB, 1, 1);
    */

    renderer = new THREE.WebGLRenderer( { antialias: true } );
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio(window.devicePixelRatio);
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


function fadeIn(model, params) {
    model.traverse(function (child) {
        if (child.material) {
            const orig_transparent = child.material.transparent;
            const orig_opacity = child.material.opacity || 1.0;
            child.material.transparent = true;
            child.material.opacity = 0;
            const new_params = Object.assign({
                on_finish: function () {
                    child.material.transparent = orig_transparent;
                }
            }, params);
            animateProps(child.material, {opacity: orig_opacity}, new_params);
        }
    });
}


function fadeOut(model, params) {
    model.name = '';
    var children = 0;
    model.traverse(function (child) {
        if (child.material) {
            children++;
            child.material.transparent = true;
            const new_params = Object.assign({
                on_finish: function () {
                    children--;
                    if (children == 0) {
                        scene.remove(model);
                    }
                }
            }, params);
            animateProps(child.material, {opacity: 0}, new_params);
        }
    });
    if (!children)
        scene.remove(model);
}

function wrapModel(model) {
    scene.remove(model);
    var wrapper = new THREE.Scene();
    wrapper.add(model)
    wrapper.position = model.position;
    model.position.set(0, 0, 0);
    scene.add(wrapper);
    return wrapper;
}

function unwrapModel(model) {
    const wrapper = model.parent;
    scene.remove(wrapper);
    model.position = wrapper.position;
    scene.add(model);
}

function teleportOut(model) {
    scene.remove(model);
    const wrapper = wrapModel(model);
    wrapper.overrideMaterial = TELEPORT;
    model.traverse(function (c) { c.castShadow = false});
    fadeOut(wrapper, {duration: 200});
    animateProps(model.scale, {y: 10}, {duration: 200});
}

function teleportIn(model) {
    const wrapper = wrapModel(model);
    wrapper.overrideMaterial = TELEPORT;
    model.traverse(function (c) { c.castShadow = false});
    model.scale.y = 10;
    scene.add(wrapper);
    fadeIn(model, {duration: 200});
    animateProps(model.scale, {y: 1}, {
        duration: 200,
        on_finish: function () {
            unwrapModel(model);
            model.traverse(function (c) { c.castShadow = true});
        }
    });
}


function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight);
}


const clock = new THREE.Clock();


function animate() {
    requestAnimationFrame( animate );
    anims.update(clock.getDelta());
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
    sun.position.set(x - 200, 200, z - 100);
    sun.target.position.set(x, 0, z);
}

function pan_camera(x, z) {
    animateProps(camera.position,
        {
            x: x - 30,
            z: z + 100,
        },
        {
            duration: 100,
            each_frame: function () {
                var cx = camera.position.x + 30;
                var cz = camera.position.z - 100;
                camera.lookAt(cx, 0, cz);
                sun.position.set(cx - 200, 200, cz - 100);
                sun.target.position.set(cx, 0, cz);
            }
        }
    );
}

function refresh(msg) {
    // Remove existing objects
    for (let i = 0; i < scene.children.length; i++) {
        let child = scene.children[i];
        if (child.worldObj) {
            scene.remove(child);
            i--;
        }
    }
    let [x, z] = to_world(msg.pos);
    move_camera(x, z);
    for (let obj of msg.objs) {
        spawn_obj(obj);
    }
    if (msg.world.sun_color)
        sun.color.set(msg.world.sun_color);
    if (msg.world.sun_intensity)
        sun.intensity = msg.world.sun_intensity;
    if (msg.world.ambient_color)
        ambient.color.set(msg.world.ambient_color);
    if (msg.world.ambient_intensity)
        ambient.intensity = msg.world.ambient_intensity;
    if (msg.world.title)
        $('h1').text(msg.world.title);
}

function on_moved(msg) {
    const obj = msg.obj;
    const existing = scene.getObjectByName(obj.name);
    const [x, z] = to_world(msg.to_pos);
    if (existing) {
        animateProps(
            existing.position,
            {
                x: x,
                z: z
            },
            {
                duration: 100
            }
        );
        animateProps(
            existing.position,
            {
                y: 4
            },
            {
                duration: 100,
                interp: INTERP.hop,
                on_finish: function () {
                    existing.position.y = 0;
                }
            }
        );
        existing.rotation.order = 'YXZ';
        var target_rotation = obj.dir * Math.PI / 2;
        animateProps(
            existing.rotation,
            {
                y: target_rotation
            },
            {
                duration: 100
            }
        );

        var hop = (Math.random() > 0.5) ? -0.1 : 0.1;
        animateProps(
            existing.rotation,
            {
                z: hop,
            },
            {
                duration: 100,
                interp: INTERP.hop,
                on_finish: function () { existing.rotation.z = 0; }
            }
        );
    } else {
        let [x, z] = to_world(msg.from_pos);
        load_model(obj, function(model) {
            model.position.x = x;
            model.position.z = z;
            on_moved(msg);
            fadeIn(model, {duration: 200});
        });
    }
    if (msg.track) {
        pan_camera(x, z);
    }
}

function on_spawned(msg) {
    spawn_obj(msg.obj, msg.effect);
}


function spawn_obj(obj, effect) {
    let [x, z] = to_world(obj.pos);
    load_model(obj, function(model) {
        if (obj.model == 'advancedCharacter') {
            load_model(
                {
                    name: 'weapon',
                    model: 'weapons/sword',
                    dir: 0,
                },
                function (sword) {
                    var grp = new THREE.Group();
                    grp.scale.set(1.5, 1.5, 1.5);
                    grp.add(sword);
                    sword.visible = false;
                    sword.play = function () {
                        sword.visible = true;
                        let clip = sword.animations[0];
                        let action = anims.clipAction(clip, sword);

                        action.loop = THREE.LoopOnce;
                        action.hide_on_finish = true;
                        action.reset();
                        action.play();
                    };

                    model.add(grp);
                }
            );
        }

        if (model.animations.length) {
            let clip = model.animations[0];
            let action = anims.clipAction(clip, model);
            grp = new THREE.Group();
            grp.name = model.name;
            grp.worldObj = true;
            model.name = '';
            grp.add(model);
            scene.add(grp);
            model = grp;
            action.play();
        }
        model.position.x = x;
        model.position.z = z;
        switch (effect) {
            case "fade":
                fadeIn(model, {duration: 200});
                break;

            case "teleport":
                teleportIn(model);
                break;
        }
    });
}

function on_killed(msg) {
    var model = scene.getObjectByName(msg.obj.name);
    var effect = msg.effect || 'none';
    if (model) {
        switch (effect) {
            case "fade":
                fadeOut(model, {duration: 200});
                break;

            case "teleport":
                teleportOut(model);
                break;

            default:
                scene.remove(model);
                break;
        }
    }
}


function on_attack(msg) {
    const model = scene.getObjectByName(msg.name);
    if (!model)
        return;
    const weapon = model.getObjectByName('weapon');
    if (!weapon)
        return;
    weapon.play()
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
    'killed': on_killed,
    'spawned': on_spawned,
    'attack': on_attack,
};


function connect() {
    ws = new WebSocket("ws://" + location.host + "/ws");

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
