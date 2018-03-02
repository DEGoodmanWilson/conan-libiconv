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
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"
    archive_name = "{0}-{1}".format(name, version)
    short_paths = True

    @property
    def is_mingw(self):
        return self.settings.os == 'Windows' and self.settings.compiler == 'gcc'

    @property
    def is_msvc(self):
        return self.settings.compiler == 'Visual Studio'

    def configure(self):
        del self.settings.compiler.libcxx

    def source(self):
        source_url = "https://ftp.gnu.org/gnu/libiconv"
        tools.get("{0}/{1}.tar.gz".format(source_url, self.archive_name))

    def build_autotools(self):
        prefix = os.path.abspath(self.package_folder)
        win_bash = False
        rc = None
        host = None
        build = None
        if self.is_mingw or self.is_msvc:
            prefix = prefix.replace('\\', '/')
            win_bash = True
            build = False
            if self.settings.arch == "x86":
                host = "i686-w64-mingw32"
                rc = "windres --target=pe-i386"
            elif self.settings.arch == "x86_64":
                host = "x86_64-w64-mingw32"
                rc = "windres --target=pe-x86-64"

        env_build = AutoToolsBuildEnvironment(self, win_bash=win_bash)
        env_build.fpic = self.options.fPIC

        configure_args = ['--prefix=%s' % prefix]
        if self.options.shared:
            configure_args.extend(['--disable-static', '--enable-shared'])
        else:
            configure_args.extend(['--enable-static', '--disable-shared'])

        env_vars = {}

        if self.is_mingw:
            configure_args.extend(['CPPFLAGS=-I%s/include' % prefix,
                                   'LDFLAGS=-L%s/lib' % prefix,
                                   'RANLIB=:'])
        if self.is_msvc:
            runtime = str(self.settings.compiler.runtime)
            configure_args.extend(['CC=$PWD/build-aux/compile cl -nologo',
                                   'CFLAGS=-%s' % runtime,
                                   'CXX=$PWD/build-aux/compile cl -nologo',
                                   'CXXFLAGS=-%s' % runtime,
                                   'CPPFLAGS=-D_WIN32_WINNT=0x0600 -I%s/include' % prefix,
                                   'LDFLAGS=-L%s/lib' % prefix,
                                   'LD=link',
                                   'NM=dumpbin -symbols',
                                   'STRIP=:',
                                   'AR=$PWD/build-aux/ar-lib lib',
                                   'RANLIB=:'])
            env_vars['win32_target'] = '_WIN32_WINNT_VISTA'

            with tools.chdir(self.archive_name):
                tools.run_in_windows_bash(self, 'chmod +x build-aux/ar-lib build-aux/compile')

        if rc:
            configure_args.extend(['RC=%s' % rc, 'WINDRES=%s' % rc])

        with tools.chdir(self.archive_name):
            with tools.environment_append(env_vars):
                env_build.configure(args=configure_args, host=host, build=build)
                env_build.make()
                env_build.make(args=["install"])

    def fix_windows_permissions(self, folder):
        """ grant ACL permissions so Cygwin has necessary access rights """
        if not os.path.isdir(folder):
            os.makedirs(folder)
        self.run('cacls %s /T /E /G "%s\\%s":F' % (folder, os.environ['USERDOMAIN'], os.environ['USERNAME']))

    def build(self):
        if self.settings.os == "Windows":
            self.fix_windows_permissions(self.build_folder)
            self.fix_windows_permissions(self.package_folder)
            if tools.os_info.detect_windows_subsystem() not in ("cygwin", "msys2"):
                raise Exception("This recipe needs a Windows Subsystem to be compiled. "
                                "You can specify a build_require to:"
                                " 'msys2_installer/latest@bincrafters/stable' or"
                                " 'cygwin_installer/2.9.0@bincrafters/stable' or"
                                " put in the PATH your own installation")
            if self.is_msvc:
                with tools.vcvars(self.settings):
                    self.build_autotools()
            elif self.is_mingw:
                self.build_autotools()
            else:
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
