if ( ! Detector.webgl ) Detector.addGetWebGLMessage();

var container, stats, controls;
var camera, scene, renderer, light, sun, ambient, anims, slash, proton;

const tex_loader = new THREE.TextureLoader();
const model_loader = new THREE.GLTFLoader();

const INTERP = {
    linear: function(x) {
        return x;
    },

    hop: function(x) {
        return -4 * x * (x - 1);
    },

    easeOut: function(x) {
        return Math.sqrt(x);
    },

    easeIn: function(x) {
        return x * x;
    },
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

const SHADOW_SIZE = 150;
const TILE_SIZE = 16;
const SLAB = new THREE.MeshBasicMaterial({
    color: 0x111111,
    side: THREE.DoubleSide,
    opacity: 0.1,
    transparent: true
});
const BLOOD = new THREE.SpriteMaterial({
    map: new THREE.TextureLoader().load("textures/droplet.png"),
    color: 0xff0000,
    lights: true
});
var VOMIT = BLOOD.clone();
VOMIT.color = 0x00ff00;

const TELEPORT = new THREE.MeshBasicMaterial({
    color: 0x1188DD,
    side: THREE.FrontSide,
    opacity: 0.5,
    transparent: true
});

const EFFECT = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    side: THREE.DoubleSide,
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

model_loader.load('models/slash.gltf', function (gltf) {
    slash = gltf.scene.children[0];
    gltf.scene.traverse((child) => {
        if (child.material) {
            child.material = EFFECT;
        }
    });
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
    controls = new THREE.OrbitControls( camera );
    controls.target.set( 0, -2, -2 );
    controls.update();
    */

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
    sun.shadow.mapSize.width = 1024;
    sun.shadow.mapSize.height = 1024;
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

    proton = new Proton();
    proton.addRender(new Proton.SpriteRender(scene));

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

function fallOut(model, params) {
    fadeOut(model, params);
    animateProps(model.rotation, {
        x: Math.PI / 2,
    }, {
        duration: params.duration,
        interp: INTERP.easeIn,
    });
}


function wrapModel(model) {
    var wrapper = new THREE.Scene();
    wrapper.position.copy(model.position);
    scene.remove(model);
    wrapper.add(model)
    model.position.set(0, 0, 0);
    scene.add(wrapper);
    return wrapper;
}

function unwrapModel(model) {
    const wrapper = model.parent;
    scene.remove(wrapper);
    model.position.copy(wrapper.position);
    scene.add(model);
}

function teleportOut(model) {
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


function growIn(model) {
    const wrapper = wrapModel(model);
    model.scale.set(0.05, 0.05, 0.05);
    scene.add(wrapper);
    animateProps(model.scale, {x: 1, y: 1, z: 1}, {
        duration: 200,
        interp: INTERP.easeOut,
        on_finish: function () {
            unwrapModel(model);
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
    proton.update();
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
    if (current_dialog)
        current_dialog.close();
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
    if (msg.world.world_tex) {
        const terrain = tex_loader.load(
            'textures/' + msg.world.world_tex + '.png'
        );
        terrain.flip_y = false;
        const mat = WORLD.clone();
        mat.map = terrain;
        ground.material = mat;
    } else {
        ground.material = WORLD;
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
    if (msg.world.title_color)
        $('h1').css({color: msg.world.title_color});
    if (msg.gold)
        $('#gold').text(msg.gold + "");
    if (msg.health)
        $('#hp').text(msg.health + "");
}

function on_setvalue(msg) {
    if (msg.gold)
        $('#gold').text(msg.gold + "");
    if (msg.health)
        $('#hp').text(msg.health + "");
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

        if (obj.title) {
            model.title = obj.title;
        }

        if (model.animations.length) {
            let clip = model.animations[0];
            let action = anims.clipAction(clip, model);
            grp = new THREE.Group();
            grp.name = model.name;
            grp.worldObj = true;
            grp.rotation.y = model.rotation.y;
            model.rotation.y = 0;
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

            case "grow":
                growIn(model);
                break;
        }
    });
}

function on_killed(msg) {
    var model = scene.getObjectByName(msg.obj.name);
    var effect = msg.effect || 'none';
    if (model) {
        model.name = '';
        switch (effect) {
            case "fade":
                fadeOut(model, {duration: 200});
                break;

            case "fall":
                fallOut(model, {duration: 500});
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


function on_update(msg) {
    const model = scene.getObjectByName(msg.obj.name);
    if (!model)
        return;

    if (msg.effect == 'attack') {
        const weapon = model.getObjectByName('weapon');
        if (!weapon)
            return;
        weapon.play();
        setTimeout(function () {fire_slash(model, -50);}, 300);
    } else if (msg.effect == 'vomit') {
        fire_particles(model, VOMIT);
    } else if (msg.effect == 'damage') {
        fire_particles(model, BLOOD);
    } else if (msg.effect == 'damage-crit') {
        fire_particles(model, BLOOD);
        fire_particles(model, BLOOD);
    } else if (msg.effect == 'light-on') {
        let light = new THREE.PointLight(0xffcc55, 1.0, 80, 2);
        light.position.set(0, 10, 8);
        //light.castShadow = true;
        model.add(light)
    } else if (msg.effect == 'light-off') {
        model.traverse((child) => {
            if (child.isLight)
                child.parent.remove(child);
        });
    }
}


function fire_slash(model, roll) {
    const s = slash.clone();
    //s.rotation.copy(model.rotation);
    s.rotation.y = model.rotation.y;
    s.rotation.z = (roll || 0) * (Math.PI / 180.0);
    s.position.set(model.position.x, 10, model.position.z);
    s.rotation.order = 'YZX';
    s.material = slash.material.clone();
    let start = new THREE.Vector3(0, 10, 3);
    start = start
        .applyQuaternion(model.quaternion)
        .add(model.position);
    let dest = new THREE.Vector3(0, 15, 20);
    dest = dest
        .applyQuaternion(model.quaternion)
        .add(model.position);
    s.name = '';
    animateProps(s.position, {
        x: dest.x,
        y: dest.y,
        z: dest.z
    }, {duration: 100});
    animateProps(s.scale, {
        x: 3,
        y: 3,
        z: 3
    }, {duration: 100});
    fadeOut(s, {duration: 100});
    scene.add(s);
}

function fire_particles(model, material) {
    var emitter = new Proton.Emitter();

    material = material.clone();

    // three.js sprites don't support lighting currently
    // Fake it by multiplying the colour by the sun's colour
    material.color = material.color.multiply(sun.color);

    //setRate
    emitter.rate = new Proton.Rate(new Proton.Span(4, 16), new Proton.Span(.01));

    //addInitialize
    //emitter.addInitialize(new Proton.Position(new Proton.PointZone(0, 0)));
    emitter.addInitialize(new Proton.Mass(1));
    emitter.addInitialize(new Proton.Radius(0.1, 1));
    emitter.addInitialize(new Proton.Life(0.3));
    emitter.addInitialize(new Proton.V(45, new Proton.Vector3D(0, 1, 0), 180));
    emitter.addInitialize(new Proton.Body(new THREE.Sprite(material)));

    //addBehaviour
    //emitter.addBehaviour(new Proton.Alpha(1, 0));
    //emitter.addBehaviour(new Proton.Scale(.1, 1.3));
    //emitter.addBehaviour(new Proton.Rotate("random", "random"));
    //emitter.addBehaviour(new Proton.Scale(1, .1));
    emitter.addBehaviour(new Proton.G(3));

    /*
    let color1 = new THREE.Color();
    let color2 = new THREE.Color();
    let colorBehaviour = new Proton.Color('#ff0000', '#000000');
    emitter.addBehaviour(colorBehaviour);
    */
    emitter.p.x = model.position.x;
    emitter.p.y = 10;
    emitter.p.z = model.position.z;

    //add emitter
    proton.addEmitter(emitter);

    emitter.emit('once');
    setTimeout(() => proton.removeEmitter(emitter), 500);
}


function on_dialog(msg) {
    switch (msg.type) {
        case "choose":
            new ChoiceDialog(msg).show();
            break;
    };
}

function on_canceldialog(msg) {
    if (current_dialog)
        current_dialog.close();
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
    'say': function (params) {
        log(
            '<' + params.user + '> ' + params.msg,
            'chat'
        );
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
    'setvalue': on_setvalue,
    'moved': on_moved,
    'killed': on_killed,
    'spawned': on_spawned,
    'update': on_update,
    'dialog': on_dialog,
};

var messages = $('<ul id="messages">').appendTo(document.body);

function connect() {
    ws = new WebSocket("ws://" + location.host + "/ws");

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
    73: 'inventory',  // I
};

var raycaster = new THREE.Raycaster();
var mouse = new THREE.Vector2();
var hover = $('<div id="hover">');


function on_mouse_move(event) {
    // calculate mouse position in normalized device coordinates
    // (-1 to +1) for both components
    mouse.x = ( event.clientX / window.innerWidth ) * 2 - 1;
    mouse.y = - ( event.clientY / window.innerHeight ) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    let named = [];
    for (let o of scene.children) {
        if (o.title)
            named.push(o);
    }
    // calculate objects intersecting the picking ray
    const intersects = raycaster.intersectObjects(named, true);

    if (!intersects.length) {
        hover.remove();
        return;
    }

    const intersection = intersects[0];
    let obj = intersection.object;
    while (!obj.title && obj.parent) {
        obj = obj.parent;
    }
    hover.text(obj.title).css({
        top: (event.clientY - 50) + 'px',
        left: (event.clientX) + 'px'
    }).appendTo(document.body);
}

function initInput() {

   $(window).bind('mousemove', on_mouse_move);


   $(window).bind('keydown', function(event) {
        var keyCode = event.which;
        if (current_dialog) {
            if (keyCode == 27) {
                current_dialog.close();
            }
            return;
        }
        op = KEYMAP[keyCode];
        if (op) {
            send_msg({'op': op});
        }
    });
}

var current_dialog = null;


class Dialog {
    constructor(type) {
        this.type = type;
    }

    show() {
        this.container = $('<div id="dialog">');

        if (current_dialog) {
            current_dialog.close();
        }
        this.container.appendTo(document.body);
        this.populate(this.container)
        this.container.css({
            top: ($(document.body).height() - this.container.height()) / 2 + 'px'
        });


        current_dialog = this;
    }

    close() {
        $(this.container).remove();
        current_dialog = null;
    }

    populate(container) {}
}


class SpeakDialog extends Dialog {
    constructor() {
        super('speak');
    }

    populate(div) {
        $('<h2>').text('Speak').appendTo(div);
        var text = $('<input>').appendTo(div);
        text.focus();
        var dlg = this;
        text.bind('keydown', function (event) {
            if (event.keyCode == 13) {
                var msg = text.val();
                dlg.close();
                send_msg({
                    'op': 'say',
                    'msg': msg
                });
            }
        });
    }
};


class ChoiceDialog extends Dialog {
    constructor(msg) {
        super('choice');
        this.title = msg.title;
        this.choices = msg.choices;
    }

    populate(div) {
        $('<h2>').text(this.title).appendTo(div);
        const container = $('<div class="choices">').appendTo(div);
        const dlg = this;
        for (let c of this.choices) {
            let item = $('<div class="item">').appendTo(container);
            item.bind('click', function () {
                send_msg({
                    'op': 'dlgresponse',
                    'value': c.key
                });
                dlg.close();
            });
            $('<img>').attr({'src': '2d/' + c.img + '.svg'}).appendTo(item);
            if (c.title) {
                $('<span class="title">').text(c.title).appendTo(item);
            }
            if (c.subtitle) {
                $('<span class="title">').text(c.subtitle).appendTo(item);
            }
        }
    }
}


$(function () {
    $('#speak').bind('click', function () {
        if (current_dialog && current_dialog.type == 'speak') {
            current_dialog.close();
        } else {
            new SpeakDialog().show();
        }
    });
    $('#inventory').bind('click', function() {
        if (current_dialog && current_dialog.type == 'choice') {
            current_dialog.close();
        } else
            send_msg({'op': 'inventory'});
    });

    init();
    initInput();
    connect();
    animate();
});
