# Nomad dev-mode config that enables Docker volume mounts.
#
# By default, Nomad's Docker driver disables bind-mounting host paths
# into containers. This tool requires volume mounts to inject the user's
# R script (and optionally a --data-dir) into the container, so this
# setting must be enabled.
#
# Usage:
#   nomad agent -dev -config=/path/to/nomad-dev.hcl
#
# On macOS with Docker Desktop, you may also need to symlink the Docker
# socket so Nomad can find it:
#   sudo ln -s ~/.docker/run/docker.sock /var/run/docker.sock

plugin "docker" {
  config {
    volumes {
      enabled = true
    }
  }
}
