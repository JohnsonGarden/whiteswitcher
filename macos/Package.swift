// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "WhiteSwitcherCore",
    platforms: [.macOS(.v14)],
    products: [.library(name: "WhiteSwitcherCore", targets: ["WhiteSwitcherCore"])],
    targets: [
        .target(name: "WhiteSwitcherCore", path: "Core"),
        .testTarget(name: "WhiteSwitcherCoreTests", dependencies: ["WhiteSwitcherCore"], path: "Tests")
    ]
)
