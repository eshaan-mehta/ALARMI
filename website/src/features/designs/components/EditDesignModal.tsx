import { useEffect } from 'react';
import {
  Button,
  Divider,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useUpdateDesign } from '../hooks';
import type { Design, DesignPatch } from '../types';

const MODULE_TYPE_OPTIONS = [
  'Wall Panel',
  'Bathroom Service Wall',
  'Hospital Headwall',
  'Utility Panel',
];
const UNIT_SCALE_OPTIONS = ['METRE', 'MILLIMETRE', 'CENTIMETRE', 'FOOT', 'INCH'];

interface Props {
  design: Design;
  projectName: string;
  opened: boolean;
  onClose: () => void;
}

interface FormValues {
  name: string;
  moduleType: string;
  dimX: number | string;
  dimY: number | string;
  dimZ: number | string;
  anchorCount: number | string;
  roomId: string;
  unitScale: string;
}

function valuesFromDesign(d: Design): FormValues {
  return {
    name: d.name,
    moduleType: d.moduleType ?? '',
    dimX: d.dimensions?.x ?? 0,
    dimY: d.dimensions?.y ?? 0,
    dimZ: d.dimensions?.z ?? 0,
    anchorCount: d.anchorCount ?? 0,
    roomId: d.roomId ?? '',
    unitScale: d.unitScale ?? '',
  };
}

export function EditDesignModal({ design, projectName, opened, onClose }: Props) {
  const update = useUpdateDesign(projectName);
  const isComplete = design.status === 'COMPLETE';

  const form = useForm<FormValues>({
    initialValues: valuesFromDesign(design),
    validate: {
      name: (v) => (v.trim().length === 0 ? 'Design name is required' : null),
    },
  });

  // Re-seed the form with the latest values each time the modal opens.
  useEffect(() => {
    if (opened) form.setValues(valuesFromDesign(design));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const handleClose = () => {
    if (update.isPending) return;
    onClose();
  };

  const handleSubmit = form.onSubmit((values) => {
    const patch: DesignPatch = { name: values.name.trim() };
    if (isComplete) {
      patch.moduleType = values.moduleType || undefined;
      patch.dimensions = {
        x: Number(values.dimX) || 0,
        y: Number(values.dimY) || 0,
        z: Number(values.dimZ) || 0,
      };
      patch.anchorCount = Number(values.anchorCount) || 0;
      patch.roomId = values.roomId || undefined;
      patch.unitScale = values.unitScale || undefined;
    }

    update.mutate(
      { designId: design.designId, patch },
      {
        onSuccess: (d) => {
          notifications.show({
            color: 'teal',
            title: 'Design updated',
            message: `“${d.name}” saved.`,
          });
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Could not save changes.')
            : 'Could not save changes.';
          notifications.show({ color: 'red', title: 'Update failed', message });
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Edit design"
      centered
      closeOnClickOutside={!update.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <TextInput
            label="Design name"
            data-autofocus
            {...form.getInputProps('name')}
          />

          {isComplete ? (
            <>
              <Divider label="Metadata" labelPosition="left" />
              <Select
                label="Type"
                data={MODULE_TYPE_OPTIONS}
                searchable
                {...form.getInputProps('moduleType')}
              />
              <Group grow>
                <NumberInput
                  label="Width x (m)"
                  min={0}
                  step={0.1}
                  decimalScale={2}
                  {...form.getInputProps('dimX')}
                />
                <NumberInput
                  label="Height y (m)"
                  min={0}
                  step={0.1}
                  decimalScale={2}
                  {...form.getInputProps('dimY')}
                />
                <NumberInput
                  label="Depth z (m)"
                  min={0}
                  step={0.1}
                  decimalScale={2}
                  {...form.getInputProps('dimZ')}
                />
              </Group>
              <Group grow>
                <NumberInput
                  label="Anchor points"
                  min={0}
                  allowDecimal={false}
                  {...form.getInputProps('anchorCount')}
                />
                <Select
                  label="Unit scale"
                  data={UNIT_SCALE_OPTIONS}
                  {...form.getInputProps('unitScale')}
                />
              </Group>
              <TextInput label="Room ID" {...form.getInputProps('roomId')} />
            </>
          ) : (
            <Text size="sm" c="dimmed">
              Metadata becomes editable once processing is complete.
            </Text>
          )}

          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={update.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={update.isPending}>
              Save changes
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
