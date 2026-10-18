FROM jenkins/jenkins:lts-jdk21

USER root

# ─── System dependencies ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    wget curl ca-certificates apt-transport-https gnupg2 git python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# ─── .NET 10 SDK via install script ──────────────────────────────────────
# Avoids apt repo SHA1 GPG key issue on Debian Trixie (jenkins:lts-jdk21 base)
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && chmod +x /tmp/dotnet-install.sh \
    && /tmp/dotnet-install.sh --version 10.0.300 --install-dir /usr/local/dotnet \
    && rm /tmp/dotnet-install.sh \
    && ln -s /usr/local/dotnet/dotnet /usr/local/bin/dotnet

ENV DOTNET_ROOT="/usr/local/dotnet"
ENV PATH="${PATH}:/usr/local/dotnet"

# ─── Node.js 22 ────────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ─── Docker CLI + Compose plugin ───────────────────────────────────────────
RUN curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
       https://download.docker.com/linux/debian bookworm stable" \
    > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Allow jenkins user to run Docker commands
RUN groupadd -f docker && usermod -aG docker jenkins

# Git: allow file:// protocol and any directory (for local workspace mount)
RUN git config --system protocol.file.allow always \
    && git config --system safe.directory '*'

# ─── Jenkins plugins ────────────────────────────────────────────────────────
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

USER jenkins

# Skip the Jenkins setup wizard
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc.yaml
