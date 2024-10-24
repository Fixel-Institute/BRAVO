/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import * as THREE from "three";
import * as math from "mathjs";

import CameraController from "./CameraController";
import TransformController from "./TransformController";
import CoordinateSystem from "./CoordinateSystem";
import ShadowLight from "./ShadowLight";

import retrieveModels from "./model-retrieval";
import Model from "./Model";
import Tractography from "./Tractography";
import VolumetricObject from "./VolumetricObject";
import SphereObject from "./SphereObject";

/**
 * Convert Byte-size R/G/B values to hex color string.
 *
 * @param {number} r - number of rows in subplot grid
 * @param {number} g - number of columns in subplot grid
 * @param {number} b - number of columns in subplot grid
 * 
 * @return {string} Hex encoded RGB value in format of RRGGBB (without #). 
 */
function rgbaToHex (r,g,b,a) {
  var outParts = [
    r.toString(16),
    g.toString(16),
    b.toString(16),
  ];

  // Pad single-digit output values
  outParts.forEach(function (part, i) {
    if (part.length === 1) {
      outParts[i] = '0' + part;
    }
  })

  return ('#' + outParts.join(''));
}


/**
 * Parse Binary STL file into Three.js BufferAttribute
 *
 * @param {bufferArray} data - Raw STL binary buffer
 * 
 * @return {Object} Dictionary {position, normal, color} containing Three.js BufferAttribute of vertices position, 
 * normal vector, and color (if available in STL)
 */
export const parseBinarySTL = (data) => {
  const reader = new DataView( data );
  const faces = reader.getUint32( 80, true );

  let r, g, b, hasColors = false, colors;
  let defaultR, defaultG, defaultB, alpha;

  var colorString = "#FFFFFF";
  var space = "LPS";

  for ( let index = 0; index < 80 - 10; index ++ ) {
    if ( ( reader.getUint32( index, false ) == 0x434F4C4F /*COLO*/ ) &&
      ( reader.getUint8( index + 4 ) == 0x52 /*'R'*/ ) &&
      ( reader.getUint8( index + 5 ) == 0x3D /*'='*/ ) ) {
      
        colorString = rgbaToHex(reader.getUint8( index + 6 ), reader.getUint8( index + 7 ), reader.getUint8( index + 8 ));
        defaultR = reader.getUint8( index + 6 ) / 255;
        defaultG = reader.getUint8( index + 7 ) / 255;
        defaultB = reader.getUint8( index + 8 ) / 255;
        alpha = reader.getUint8( index + 9 ) / 255;
    }

    if ( ( reader.getUint32( index, false ) == 0x53504143 /*SPAC*/ ) &&
      ( reader.getUint8( index + 4 ) == 0x45 /*'E'*/ ) &&
      ( reader.getUint8( index + 5 ) == 0x3D /*'='*/ ) ) {

        if ( (reader.getUint8( index + 6 ) == 0x4C) && (reader.getUint8( index + 7 ) == 0x50) && (reader.getUint8( index + 8 ) == 0x53) ) {
          space = "LPS";
        } else if ( (reader.getUint8( index + 6 ) == 0x52) && (reader.getUint8( index + 7 ) == 0x41) && (reader.getUint8( index + 8 ) == 0x53) ) {
          space = "RAS";
        } else {
          console.log("Unaccounted Space Type");
        }

    }
  }

  const dataOffset = 84;
  const faceLength = 12 * 4 + 2;

  const vertices = new Float32Array( faces * 3 * 3 );
  const normals = new Float32Array( faces * 3 * 3 );

  for ( let face = 0; face < faces; face ++ ) {
    const start = dataOffset + face * faceLength;
    const normalX = reader.getFloat32( start, true );
    const normalY = reader.getFloat32( start + 4, true );
    const normalZ = reader.getFloat32( start + 8, true );

    if ( hasColors ) {
      const packedColor = reader.getUint16( start + 48, true );
      if ( ( packedColor & 0x8000 ) === 0 ) {
        // facet has its own unique color
        r = ( packedColor & 0x1F ) / 31;
        g = ( ( packedColor >> 5 ) & 0x1F ) / 31;
        b = ( ( packedColor >> 10 ) & 0x1F ) / 31;
      } else {
        r = defaultR;
        g = defaultG;
        b = defaultB;
      }
    }

    for ( let i = 1; i <= 3; i ++ ) {

      const vertexstart = start + i * 12;
      const componentIdx = ( face * 3 * 3 ) + ( ( i - 1 ) * 3 );

      if (space == "RAS") {
        vertices[ componentIdx ] = -reader.getFloat32( vertexstart, true );
        vertices[ componentIdx + 1 ] = -reader.getFloat32( vertexstart + 4, true );
        vertices[ componentIdx + 2 ] = reader.getFloat32( vertexstart + 8, true );
        normals[ componentIdx ] = -normalX;
        normals[ componentIdx + 1 ] = -normalY;
        normals[ componentIdx + 2 ] = normalZ;
      } else {
        vertices[ componentIdx ] = reader.getFloat32( vertexstart, true );
        vertices[ componentIdx + 1 ] = reader.getFloat32( vertexstart + 4, true );
        vertices[ componentIdx + 2 ] = reader.getFloat32( vertexstart + 8, true );
        normals[ componentIdx ] = normalX;
        normals[ componentIdx + 1 ] = normalY;
        normals[ componentIdx + 2 ] = normalZ;
      }

      if ( hasColors ) {
        colors[ componentIdx ] = r;
        colors[ componentIdx + 1 ] = g;
        colors[ componentIdx + 2 ] = b;
      }
    }
  }

  return {
    position: new THREE.BufferAttribute( vertices, 3 ),
    normal: new THREE.BufferAttribute( normals, 3 ),
    color: colorString
  };
}

/**
 * Return Identity Matrix for Transformation. 
 *
 * @return {THREE.Matrix4} Identity Matrix where diagonal of the matrix are 1 and everywhere else 0.
 */
export const identityMatrix = () => {
  const matrix = new THREE.Matrix4();
  matrix.set(1, 0, 0, 0,
             0, 1, 0, 0,
             0, 0, 1, 0,
             0, 0, 0, 1);
  return matrix;
}

/**
 * Compute Affine Matrix to transform electrode model to patient-specific electrode location
 *
 * @param {number[]} targetPts - 3-dimensional point value in brain space for tip of electrode
 * @param {number[]} entryPts - 3-dimensional point value in brain space for any point along the trajectory above tip
 * 
 * @return {THREE.Matrix4} Affine matrix that defines 3D transformation of the electrode model.
 */
export const computeElectrodePlacement = (targetPts, entryPts) => {
  const default_lead_model = math.matrix([[0,0,0,1],[0,1,0,1],[0,0,1,1],[1,0,0,1]]);
  const target = math.matrix(math.dotMultiply(targetPts, [-1, -1, 1]));
  const entry = math.matrix(math.dotMultiply(entryPts, [-1, -1, 1]));
  const zDirection = math.subtract(entry, target);

  const K = math.divide(zDirection, math.norm(zDirection));
  const temp = math.divide(math.subtract(math.add(target, 5), target), math.norm(math.subtract(math.add(target, 5), target)));
  const I = math.divide(math.subtract(0, math.cross(K, temp)), math.norm(math.subtract(0, math.cross(K, temp))));
  const J = math.divide(math.subtract(0, math.cross(I, K)), math.norm(math.subtract(0, math.cross(I, K))));
  
  const template_coordinates = math.matrix([target, math.add(K, target), math.add(J, target), math.add(I, target)]);
  const template_coordinates_matrix = math.resize(template_coordinates, [4,4], 1);
  const transform_matrix = math.transpose(math.multiply(math.inv(default_lead_model), template_coordinates_matrix));
  
  const affine_matrix = new THREE.Matrix4();
  affine_matrix.set(...transform_matrix.reshape([16])._data);
  return affine_matrix;
}

export {
  TransformController,
  CameraController,
  CoordinateSystem,
  ShadowLight,

  Model,
  VolumetricObject,
  SphereObject,
  Tractography,

  retrieveModels
};