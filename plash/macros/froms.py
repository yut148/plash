from plash.eval import register_macro, hint
from plash import utils
from functools import wraps
import subprocess
import atexit


@register_macro()
def workaround_unionfs():
    return '''if [ -d /etc/apt/apt.conf.d ]; then
echo 'Dir::Log::Terminal "/dev/null";' > /etc/apt/apt.conf.d/unionfs_workaround
echo 'APT::Sandbox::User "root";' >> /etc/apt/apt.conf.d/unionfs_workarounds
: See https://github.com/rpodgorny/unionfs-fuse/issues/78
chown root:root /var/cache/apt/archives/partial || true
fi'''

def cache_container_hint(cache_key_templ):
    def decorator(func):
        @wraps(func)
        def wrapper(image):
            cache_key = cache_key_templ.format(image)
            container_id = utils.plash_map(cache_key)
            if not container_id:
                container_id = func(image)
                utils.plash_map(cache_key, container_id)
            return hint('image', container_id)
        return wrapper
    return decorator

@register_macro()
@cache_container_hint('docker:{}')
def from_docker(image):
    'use image from local docker'
    subprocess.check_call(['docker', 'pull', image], stdout=2)
    container = subprocess.check_output(['docker', 'create', image, 'sh']).decode().rstrip('\n')
    docker_export = subprocess.Popen(['docker', 'export', container], stdout=subprocess.PIPE)
    atexit.register(lambda: docker_export.kill())
    return subprocess.check_output(['plash', 'import-tar'], stdin=docker_export.stdout).decode().rstrip('\n')

@register_macro()
@cache_container_hint('lxcimages:{}')
def from_lxcimages(image):
    'use images from images.linuxcontainers.org'
    return subprocess.check_output(['plash', 'import-lxcimages', image]).decode().rstrip('\n')

@register_macro()
def from_id(image):
    'specify the image from an image id'
    return hint('image', image)

class MapDoesNotExist(Exception):
    pass

@register_macro()
def from_map(map_key):
    'use resolved map as image'
    image_id = subprocess.check_output(['plash-map', map_key]).decode().strip('\n')
    if not image_id:
        raise MapDoesNotExist('map {} not found'.format(repr(map_key)))
    return hint('image', image_id)

@register_macro('from')
def from_(image):
    'guess from where to take the image'
    if image.isdigit():
        return from_id(image)
    else:
        return from_lxcimages(image)