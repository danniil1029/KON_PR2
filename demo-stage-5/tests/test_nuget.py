"""Проверки чтения NuGet без доступа к сети."""

import json
import unittest
from unittest.mock import patch

from src.nuget import NugetRepository, Package, read_dependencies
from src.versions import lowest_version, root_version

MANIFEST = b"""
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <dependencies>
      <group targetFramework=".NETStandard2.0">
        <dependency id="StandardOnly" version="1.0"/>
      </group>
      <group targetFramework="net8.0">
        <dependency id="Child" version="[1.2,2.0)"/>
      </group>
      <group targetFramework="net9.0"/>
    </dependencies>
  </metadata>
</package>
"""


class NugetTests(unittest.TestCase):
    """Проверить диапазоны, платформы и загрузку метаданных."""

    def test_versions(self):
        """Отличать числовой порядок, prerelease и типы границ."""
        versions = ["1.2.0", "1.10.0", "2.0.0-beta.2", "2.0.0-beta.10"]
        self.assertEqual(root_version(versions, None), "1.10.0")
        self.assertEqual(root_version(versions, "1.2"), "1.2.0")
        self.assertEqual(lowest_version(versions, "(1.2,2.0)"), "1.10.0")
        self.assertEqual(lowest_version(versions, "[1.2]"), "1.2.0")
        self.assertEqual(lowest_version(versions, "1.3"), "1.10.0")
        self.assertIsNone(lowest_version(versions, "(,1.2)"))
        self.assertEqual(lowest_version(versions, "2.0.0-beta.3"),
                         "2.0.0-beta.10")

    def test_framework_groups(self):
        """Выбрать одну группу, в том числе явно пустую."""
        self.assertEqual(read_dependencies(MANIFEST, "net8.0"),
                         [("Child", "[1.2,2.0)")])
        self.assertEqual(read_dependencies(MANIFEST, "net7.0"),
                         [("StandardOnly", "1.0")])
        self.assertEqual(read_dependencies(MANIFEST, "net9.0"), [])
        with self.assertRaisesRegex(ValueError, "нет группы"):
            read_dependencies(MANIFEST, "net472")

    @patch("src.nuget.fetch")
    def test_repository(self, fetch):
        """Скачать манифест и подобрать версию прямой зависимости."""
        service = "https://example.test/v3/index.json"
        base = "https://example.test/flat"
        fetch.side_effect = [
            json.dumps({"resources": [{
                "@type": "PackageBaseAddress/3.0.0", "@id": base + "/",
            }]}),
            '{"versions": ["1.0.0"]}',
            MANIFEST,
            '{"versions": ["1.2.0", "1.8.0", "2.0.0"]}',
        ]
        repository = NugetRepository(service)
        package = repository.root("Example")
        self.assertEqual(repository.dependencies(package),
                         [Package("child", "1.2.0")])
        self.assertEqual(repository.versions("example"), ["1.0.0"])
        urls = [call.args[0] for call in fetch.call_args_list]
        self.assertEqual(urls, [
            service, base + "/example/index.json",
            base + "/example/1.0.0/example.nuspec",
            base + "/child/index.json",
        ])
