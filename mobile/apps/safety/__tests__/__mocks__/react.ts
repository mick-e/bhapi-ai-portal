// Mock React for testing without React Native runtime
const createElement = jest.fn(
  (type: any, props: any, ...children: any[]) => ({
    type,
    props: { ...props, children: children.length === 1 ? children[0] : children },
  })
);

const useEffect = jest.fn((fn: Function) => fn());
const useState = jest.fn((initial: any) => [initial, jest.fn()]);

module.exports = {
  default: { createElement, useEffect, useState },
  createElement,
  useEffect,
  useState,
};
