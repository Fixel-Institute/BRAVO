import * as THREE from "three";

function ShadowLight({x, y, z, color, intensity}) {
  const d = 1;
  const orthoCamera = new THREE.OrthographicCamera(-d, d, d, -d, 1, 4)
  return <directionalLight args={[color, intensity]} position={[x, y, z]} castShadow shadow={{bias: -0.002, camera: orthoCamera}} />;
}

export default ShadowLight;