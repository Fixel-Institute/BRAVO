import React from "react";
import { useThree } from "@react-three/fiber";

function TransformController({transformMatrix}) {
  const { scene } = useThree();
  React.useEffect(() => {
    scene.matrixAutoUpdate = false;
    scene.matrixWorld = transformMatrix;
    scene.updateWorldMatrix();
    console.log(scene);
  }, [transformMatrix])
}

export default TransformController;