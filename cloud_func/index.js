const {spawnSync} = require('child_process');
const ffi = require('ffi');
const fs = require('fs');

const ArrayType = require('ref-array');
const lib = ffi.Library('libc', {
    'execvp': ['int', ['string', ArrayType('string')]],
    'execvpe': ['int', ['string', ArrayType('string'), ArrayType('string')]],
    'fcntl': ['int', ['int', 'int', 'int']],
});

function execvpe(program, arguments, environment) {
    const arr = [
        program,
        ...arguments,
        null
    ];
    const env = [
        ...environment,
        null
    ];
    lib.execvpe(program, arr, env);
    // Program should be dead after this point.
    throw Error("execvpe failed to make the switch");
}

function unsetCloseOnExec(descriptor) {
    const F_GETFD = 1;
    const F_SETFD = 2;
    const FD_CLOEXEC = 1;
    const flags = lib.fcntl(descriptor, F_GETFD, 0);
    lib.fcntl(descriptor, F_SETFD, (flags & ~FD_CLOEXEC));
}

function changeToPython(server_socket, load_socket) {
    // Drop the descriptor on the floor
    unsetCloseOnExec(server_socket);
    unsetCloseOnExec(load_socket);
    unsetCloseOnExec(0);
    unsetCloseOnExec(1);
    unsetCloseOnExec(2);
    //console.error('replacing with python now!', {descriptor});
    const pythonhome = `${process.cwd()}/python`;
    const app = `${pythonhome}/bin/python`;
    const args = ['-m', 'worker'];
    const env = [
        ...Object.keys(process.env).map(key => {
            return `${key}=${process.env[key]}`;
        }),
        `PYTHONHOME=${pythonhome}`,
        `PYTHONPATH=${pythonhome}`,
        `SERVER_DESCRIPTOR=${server_socket}`,
        `LOAD_DESCRIPTOR=${load_socket}`,
    ];
    // Close your eyes and forget all about node.
    execvpe(app, args, env);
}

const port = parseInt(process.env.X_GOOGLE_WORKER_PORT);
const output = fs.readdirSync('/proc/self/fdinfo');
let sockets = output.map(d => {
    try {
        const data = spawnSync('stat', [`/proc/${process.pid}/fd/${d}`], {encoding: 'utf8'});
        if (data.stdout.includes('socket')) {
            return d;
        }
    } catch (err) {
    }
    return null;
}).filter(s => s !== null).map(s => parseInt(s)).sort((a,b) => a-b);

console.log(`Descriptors: ${output.length} - Sockets: ${sockets.length}`);
const [descriptor, load_socket] = [sockets[0], sockets.slice(-1)[0]];
console.log("Queueing for python to take over.");
changeToPython(descriptor, load_socket);
