/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useRef, forwardRef } from "react";

// Dropzone components
import Dropzone from "dropzone";
import "dropzone/dist/dropzone.css";

import MDBox from "components/MDBox";
import { usePlatformContext } from "context";

const DropzoneUploader = forwardRef(({ options }, ref) => {
  const [controller] = usePlatformContext();
  
  useEffect(() => {
    Dropzone.autoDiscover = false;
    const zone = new Dropzone(ref.current, { ...options });
    
    return () => {
      if (Dropzone.instances.length > 0) Dropzone.instances.forEach((dz) => dz.destroy());
    }

  }, [options]);

  return (
    <MDBox
      component="form"
      ref={ref}
      className="form-control dropzone"
    >
      <MDBox className="fallback" bgColor="transparent">
        <MDBox component="input" name="file" type="file" multiple />
      </MDBox>
    </MDBox>
  );
})

export default DropzoneUploader;
