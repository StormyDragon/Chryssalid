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

function changeToPython(...sockets) {
    // Bring a select elite of file descriptors with us to the glory days.
    for (const socket of sockets) {
        unsetCloseOnExec(socket);
    }
    unsetCloseOnExec(0);
    unsetCloseOnExec(1);
    unsetCloseOnExec(2);
    const pythonhome = `${process.cwd()}/python`;
    const app = `${pythonhome}/bin/python`;
    const args = ['-m', 'worker'];
    const env = [
        ...Object.keys(process.env).map(key => {
            return `${key}=${process.env[key]}`;
        }),
        `PATH=${pythonhome}/bin:${process.env.PATH}`,
        `SOCKET_TRANSFERRENCE=${sockets.join('_')}`,
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
}).filter(s => s !== null).map(s => parseInt(s)).sort((a, b) => a - b);

console.log(`Descriptors: ${output.length} - Sockets: ${sockets.length}`);
console.log("Queueing for python to take over.");
changeToPython(...sockets);

module.exports = {
    'hello-trigger': (req, res) => {
        const pythonhome = `${process.cwd()}/python`;
        const app = `${pythonhome}/bin/python`;
        const env = [
            ...Object.keys(process.env).map(key => {
                return `${key}=${process.env[key]}`;
            }),
            `PATH=${pythonhome}/bin:${process.env.PATH}`,
            `SOCKET_TRANSFERRENCE=${sockets.join('_')}`,
        ];
        const data = spawnSync(app, [`--version`], {encoding: 'utf8', env, timeout: 10000});
        console.log("Doing...", {app, data});
        res.status(200).send('OK');
    }
};
