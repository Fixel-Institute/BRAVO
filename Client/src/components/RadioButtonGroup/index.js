/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";

import {
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio
} from "@mui/material";

const RadioButtonGroup = ({defaultValue, options, row, onChange}) => {
  return (
    <RadioGroup
      value={defaultValue}
      row={row}
      onChange={onChange}
    >
      {options.map((option) => {
        return <FormControlLabel key={option.value} value={option.value} control={<Radio />} label={option.label} />
      })}
    </RadioGroup>
  );
};

export default RadioButtonGroup;