#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment
import os


class LibiconvConan(ConanFile):
    name = "libiconv"
    version = "1.15"
    description = "Convert text to and from Unicode"
    url = "https://github.com/bincrafters/conan-libiconv"
    license = "LGPL-2.1"
    exports = ["LICENSE.md"]
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False] }
    default_options = "shared=False", "fPIC=True"
    archive_name = "{0}-{1}".format(name, version)

    def configure(self):
        del self.settings.compiler.libcxx

    def source(self):
        source_url = "https://ftp.gnu.org/gnu/libiconv"
        tools.get("{0}/{1}.tar.gz".format(source_url, self.archive_name))

    def build_autotools(self):
        env_build = AutoToolsBuildEnvironment(self)
        env_build.fpic = self.options.fPIC
        configure_args = ['--prefix=%s' % os.path.abspath(self.package_folder)]
        if self.options.shared:
            configure_args.extend(['--disable-static', '--enable-shared'])
        else:
            configure_args.extend(['--enable-static', '--disable-shared'])
        with tools.chdir(self.archive_name):
            env_build.configure(args=configure_args)
            env_build.make()
            env_build.make(args=["install"])

    def run_in_cygwin(self, command):
        with tools.environment_append({'PATH': [self.deps_env_info['cygwin_installer'].CYGWIN_BIN]}):
            bash = "%CYGWIN_BIN%\\bash"
            vcvars_command = tools.vcvars_command(self.settings, force=True)
            self.run("{vcvars_command} && {bash} -c ^'{command}'".format(
                vcvars_command=vcvars_command,
                bash=bash,
                command=command))

    def build_vs(self):
        # README.windows
        if self.settings.arch == "x86":
            host = "i686-w64-mingw32"
        elif self.settings.arch == "x86_64":
            host = "x86_64-w64-mingw32"
        else:
            raise Exception("unsupported architecture %s" % self.settings.arch)
        prefix = tools.unix_path(os.path.abspath(self.package_folder))
        if self.options.shared:
            options = '--disable-static --enable-shared'
        else:
            options = '--enable-static --disable-shared'

        with tools.chdir(self.archive_name):
            self.run_in_cygwin('chmod a+x build-aux/ar-lib build-aux/compile')
            self.run_in_cygwin('win32_target=_WIN32_WINNT_VISTA ./configure '
                               '{options} '
                               '--host={host} '
                               '--prefix={prefix} '
                               'CC="$PWD/build-aux/compile cl -nologo" '
                               'CFLAGS="-{runtime}" '
                               'CXX="$PWD/build-aux/compile cl -nologo" '
                               'CXXFLAGS="-{runtime}" '
                               'CPPFLAGS="-D_WIN32_WINNT=0x0600 -I{prefix}/include" '
                               'LDFLAGS="-L{prefix}/lib" '
                               'LD="link" '
                               'NM="dumpbin -symbols" '
                               'STRIP=":" '
                               'AR="$PWD/build-aux/ar-lib lib" '
                               'RANLIB=":" '.format(host=host, prefix=prefix, options=options,
                                                    runtime=str(self.settings.compiler.runtime)))
            self.run_in_cygwin('make -j%s' % tools.cpu_count())
            self.run_in_cygwin('make install')

    def build_mingw(self):
        raise Exception("not implemented")

    def build(self):
        if self.settings.os == "Windows":
            if self.settings.compiler == "Visual Studio":
                self.build_vs()
            elif self.settings.compiler == "gcc":
                self.build_mingw()
            else:
                # TODO : clang on Windows and others
                raise Exception("unsupported build")
        else:
            self.build_autotools()

    def package(self):
        self.copy(os.path.join(self.archive_name, "COPYING.LIB"), dst="licenses", ignore_case=True, keep_path=False)

    def package_info(self):
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.libs = ['iconv.dll.lib']
        else:
            self.cpp_info.libs = ['iconv']
        self.env_info.path.append(os.path.join(self.package_folder, "bin"))
