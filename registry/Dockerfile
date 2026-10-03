# Internal package registry — the "trusted" source the victim pulls from.
FROM python:3.12-slim

# pypiserver >=2.1 dropped the distutils import that breaks on Python 3.12+.
RUN pip install --no-cache-dir pypiserver==2.3.2 build

WORKDIR /build
COPY malicious-pkg/ /build/malicious-pkg/

# Build the poisoned package into an sdist and drop it in the served index.
RUN mkdir -p /packages \
    && cd /build/malicious-pkg \
    && python -m build --sdist --outdir /packages

EXPOSE 8080
# -P . -a . = no auth, anonymous — like a misconfigured internal registry.
CMD ["pypi-server", "run", "-p", "8080", "-P", ".", "-a", ".", "/packages"]
